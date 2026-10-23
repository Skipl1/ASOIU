import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.config import get_settings
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import NutritionReport, User
from app.services.analysis import analyze
from app.services.audit import log_action
from app.services.reports import EXPORTERS, MEDIA_TYPES, build_report

router = APIRouter(tags=["reports"])


@router.get("/reports/nutrition", response_model=schemas.NutritionReportOut, summary="Отчёт о пищевой ценности за период")
def nutrition_report(
    date_from: date = Query(alias="dateFrom"),
    date_to: date = Query(alias="dateTo"),
    goal_id: uuid.UUID | None = Query(default=None, alias="goalId"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_report(db, user, date_from, date_to, goal_id).out


@router.post("/reports/nutrition/export", response_model=schemas.ReportExportResponse, summary="Экспорт отчёта в PDF / XLSX / CSV")
def export_report(body: schemas.ReportExportRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = build_report(db, user, body.date_from, body.date_to, body.goal_id)
    content = EXPORTERS[body.format](data)
    report = NutritionReport(
        user_id=user.user_id,
        fitness_goal_id=body.goal_id,
        period_start=body.date_from,
        period_end=body.date_to,
        export_format=body.format,
        total_calories=data.out.total_calories,
        average_calories=data.out.average_calories,
        total_protein_g=data.out.total_protein,
        total_fat_g=data.out.total_fat,
        total_carb_g=data.out.total_carbs,
        recipes_count=data.out.recipes_count,
    )
    db.add(report)
    db.flush()
    file_name = f"report_{body.date_from:%Y%m%d}_{body.date_to:%Y%m%d}_{str(report.report_id)[:8]}.{body.format}"
    folder = get_settings().reports_dir / str(user.user_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / file_name).write_bytes(content)
    report.file_name = file_name
    log_action(db, "report_export", user.user_id, entity="nutrition_reports", entity_id=report.report_id,
               details={"format": body.format}, ip=client_ip(request))
    db.commit()
    return schemas.ReportExportResponse(
        report_id=report.report_id, download_url=f"/api/v1/reports/{report.report_id}/download", file_name=file_name
    )


def _file_path(user_id: uuid.UUID, report: NutritionReport) -> Path | None:
    if not report.file_name:
        return None
    path = get_settings().reports_dir / str(user_id) / report.file_name
    return path if path.exists() else None


@router.get("/reports", response_model=list[schemas.SavedReportOut], summary="История сохранённых отчётов")
def saved_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(NutritionReport).where(NutritionReport.user_id == user.user_id).order_by(NutritionReport.formed_at.desc()))
    return [
        schemas.SavedReportOut(
            report_id=r.report_id, date_from=r.period_start, date_to=r.period_end, format=r.export_format,
            goal_name=r.goal.name if r.goal else None, formed_at=r.formed_at, average_calories=r.average_calories,
            total_protein=r.total_protein_g, total_fat=r.total_fat_g, total_carbs=r.total_carb_g,
            recipes_count=r.recipes_count, file_available=_file_path(user.user_id, r) is not None,
        )
        for r in rows
    ]


@router.get("/reports/{report_id}/download", summary="Скачать файл отчёта", response_class=FileResponse)
def download_report(report_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(NutritionReport, report_id)
    if report is None or report.user_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Отчёт не найден")
    path = _file_path(user.user_id, report)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Файл отчёта отсутствует в хранилище")
    return FileResponse(path, media_type=MEDIA_TYPES[report.export_format], filename=report.file_name)


@router.get("/analysis/nutrition", response_model=schemas.NutritionAnalysis, tags=["analysis"], summary="Анализ соответствия рациона цели")
def nutrition_analysis(
    date_from: date = Query(alias="dateFrom"),
    date_to: date = Query(alias="dateTo"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analyze(db, user, date_from, date_to)
