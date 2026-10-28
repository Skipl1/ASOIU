workspace "АС ГРСН" "C4-модель автоматизированной системы генерации персонализированных рецептов спортивного питания." {

    !identifiers hierarchical

    model {
        user = person "Пользователь" "Ведёт профиль, запреты, ингредиенты, рецепты, рацион и отчёты"
        admin = person "Администратор" "Управляет пользователями, справочниками, логами и резервными копиями"

        grsn = softwareSystem "АС ГРСН" "Генерация персонализированных рецептов спортивного питания" {
            web = container "Web-интерфейс" "Пользовательские и административные страницы; Nginx отдаёт приложение и проксирует запросы /api" "React 18, Nginx"

            api = container "REST API" "Бизнес-логика модулей, генерация рецептов, экспорт отчётов, резервное копирование по запросу администратора" "FastAPI, Uvicorn, OpenAPI, JWT" {
                router = component "API Router" "Маршрутизирует запросы /api/v1, проверяет JWT и роль" "FastAPI routers"
                auth = component "AuthService" "Регистрация, вход, bcrypt, JWT, блокировка при подборе пароля" "FastAPI service"
                profile = component "ProfileService" "Профиль, история замеров, BMR, TDEE и цель" "FastAPI service"
                restrictions = component "RestrictionService" "Запреты, нормализация и правило проверки рецепта" "FastAPI service"
                ingredients = component "IngredientService" "Каталог и доступный набор ингредиентов" "FastAPI service"
                generation = component "RecipeGenerationService" "Контекст генерации, пожелания, проверка ответа модели, сохранение" "FastAPI service"
                gigachat = component "GigaChatProvider" "Запрос к GigaChat по JSON-схеме, очередь в один поток" "GigaChat SDK"
                localGen = component "LocalGenerator" "Резервный локальный генератор рецептов" "Python"
                optimizer = component "MassOptimizer" "Подбор масс: взвешенный МНК, метод проекции градиента" "Python"
                nutrition = component "NutritionCalculator" "Расчёт БЖУ, калорийности и отклонений" "Python"
                history = component "RecipeHistoryService" "История, оценки, рацион, редактирование рецептов" "FastAPI service"
                reports = component "ReportService" "Отчёты за период, экспорт PDF, XLSX, CSV" "FastAPI service"
                analysis = component "AnalysisService" "Сравнение с целью, тренды веса, прогноз, рекомендации" "FastAPI service"
                adminService = component "AdminService" "Пользователи, справочники, журнал событий, целостность данных" "FastAPI service"
                backupService = component "BackupService" "Копирование и восстановление БД по запросу администратора" "pg_dump, pg_restore"
            }

            db = container "База данных" "Пользователи, профили, НСИ, рецепты, отчёты и журнал событий" "PostgreSQL 15" {
                tags "Database"
            }

            backup = container "Сервис резервного копирования" "Ежедневная полная копия базы данных по расписанию, хранение 30 дней" "cron, pg_dump"

            reportStore = container "Хранилище отчётов" "Файлы экспортированных отчётов PDF, XLSX и CSV" "Файловый том" {
                tags "Storage"
            }

            backupStore = container "Хранилище резервных копий" "Файлы резервных копий на отдельном диске сервера" "Отдельный диск" {
                tags "Storage"
            }
        }

        llm = softwareSystem "GigaChat API" "Большая языковая модель GigaChat-2-Pro (ПАО «Сбербанк»), создаёт варианты рецептов" {
            tags "External"
        }

        user -> grsn "Использует функции питания" "HTTPS"
        admin -> grsn "Администрирует систему" "HTTPS"
        grsn -> llm "Запрашивает рецепт" "HTTPS, JSON"

        user -> grsn.web "Использует" "HTTPS"
        admin -> grsn.web "Администрирует" "HTTPS"
        grsn.web -> grsn.api "Вызывает REST API" "JSON/HTTPS"
        grsn.api -> grsn.db "Читает и пишет" "SQL"
        grsn.api -> llm "Запрашивает рецепт" "HTTPS, JSON"
        grsn.api -> grsn.reportStore "Сохраняет отчёты" "PDF, XLSX, CSV"
        grsn.api -> grsn.backupStore "Ручная копия и восстановление" "pg_dump, pg_restore"
        grsn.backup -> grsn.db "Считывает данные" "pg_dump"
        grsn.backup -> grsn.backupStore "Сохраняет копии" "Файлы"

        grsn.web -> grsn.api.router "Вызывает REST API" "JSON/HTTPS"
        grsn.api.router -> grsn.api.auth "/auth"
        grsn.api.router -> grsn.api.profile "/profile"
        grsn.api.router -> grsn.api.restrictions "/restrictions"
        grsn.api.router -> grsn.api.ingredients "/ingredients"
        grsn.api.router -> grsn.api.generation "/recipes/generate"
        grsn.api.router -> grsn.api.history "/recipes"
        grsn.api.router -> grsn.api.reports "/reports"
        grsn.api.router -> grsn.api.analysis "/analysis"
        grsn.api.router -> grsn.api.adminService "/admin"
        grsn.api.router -> grsn.api.backupService "/admin/backups"

        grsn.api.generation -> grsn.api.gigachat "Контекст рецепта"
        grsn.api.generation -> grsn.api.localGen "При недоступности модели"
        grsn.api.generation -> grsn.api.optimizer "Массы ингредиентов"
        grsn.api.generation -> grsn.api.restrictions "Проверка запретов"
        grsn.api.generation -> grsn.api.nutrition "БЖУ и калорийность"
        grsn.api.localGen -> grsn.api.optimizer "Массы ингредиентов"
        grsn.api.gigachat -> llm "Запрос рецепта" "HTTPS, JSON"

        grsn.api.auth -> grsn.db "Пользователи и пароли" "SQL"
        grsn.api.profile -> grsn.db "Профили, замеры, цели" "SQL"
        grsn.api.restrictions -> grsn.db "Запреты и аллергены" "SQL"
        grsn.api.ingredients -> grsn.db "Каталог и набор" "SQL"
        grsn.api.generation -> grsn.db "Запросы и рецепты" "SQL"
        grsn.api.history -> grsn.db "Рецепты и оценки" "SQL"
        grsn.api.reports -> grsn.db "Рецепты рациона, отчёты" "SQL"
        grsn.api.reports -> grsn.reportStore "PDF, XLSX, CSV"
        grsn.api.analysis -> grsn.db "Рацион и замеры" "SQL"
        grsn.api.adminService -> grsn.db "Пользователи и справочники" "SQL"
        grsn.api.backupService -> grsn.db "Копия и восстановление" "pg_dump, pg_restore"
        grsn.api.backupService -> grsn.backupStore "Файлы копий"
    }

    views {
        systemContext grsn "C4_Context_AS_GRSN" {
            title "Контекстная C4-модель АС ГРСН"
            include user
            include admin
            include grsn
            include llm
            autolayout lr
        }

        container grsn "C4_Container_AS_GRSN" {
            title "Контейнерная C4-модель АС ГРСН"
            include *
            autolayout lr
        }

        component grsn.api "C4_Component_Backend_API" {
            title "Компонентная C4-модель backend REST API АС ГРСН"
            include *
            autolayout tb 220 60
        }

        styles {
            element "Person" {
                background #083F75
                color #ffffff
                shape person
            }

            element "Software System" {
                background #1061B0
                color #ffffff
                shape roundedbox
            }

            element "External" {
                background #8C8496
                color #ffffff
                shape roundedbox
            }

            element "Container" {
                background #23A2D9
                color #ffffff
                shape roundedbox
            }

            element "Component" {
                background #85BBF0
                color #ffffff
                shape roundedbox
            }

            element "Database" {
                shape cylinder
            }

            element "Storage" {
                shape folder
            }

            element "Boundary" {
                strokeWidth 5
            }

            relationship "Relationship" {
                thickness 3
                dashed true
            }
        }
    }

    configuration {
        scope softwaresystem
    }
}
