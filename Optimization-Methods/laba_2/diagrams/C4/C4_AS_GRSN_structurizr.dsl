workspace "АС ГРСН" "C4-модель автоматизированной системы генерации персонализированных рецептов спортивного питания." {

    !identifiers hierarchical

    model {
        user = person "Пользователь" "Ведёт профиль, запреты, ингредиенты, рецепты и отчёты"
        admin = person "Администратор" "Управляет пользователями, справочниками, логами и backup"

        grsn = softwareSystem "АС ГРСН" "Генерация персонализированных рецептов спортивного питания" {
            web = container "Web-интерфейс" "Пользовательские и административные страницы" "React"

            api = container "REST API" "Авторизация и бизнес-логика модулей" "FastAPI, OpenAPI, JWT" {
                router = component "API Router" "Маршрутизирует REST-запросы" "FastAPI routes"
                auth = component "AuthService" "Регистрация, вход, bcrypt и JWT" "FastAPI service"
                profile = component "ProfileService" "Профиль, BMR, TDEE и цель" "FastAPI service"
                restrictions = component "RestrictionService" "Запреты, аллергены и сопоставление" "FastAPI service"
                ingredients = component "IngredientService" "Каталог и доступный набор" "FastAPI service"
                recipe = component "RecipeGenerationService" "Генерация и проверка рецепта" "FastAPI service"
                history = component "RecipeHistoryService" "История рецептов и оценка" "FastAPI service"
                reports = component "ReportService" "Пищевые отчёты и экспорт" "FastAPI service"
                analysis = component "AnalysisService" "Сравнение с целью и рекомендации" "FastAPI service"
                adminService = component "AdminService" "Администрирование и backup" "FastAPI service"
            }

            db = container "База данных" "Пользователи, профили, НСИ, рецепты, отчёты и логи" "PostgreSQL" {
                tags "Database"
            }

            exporter = container "Сервис экспорта" "Формирует PDF, XLSX и CSV" "Backend component"
            backup = container "Сервис backup" "Создаёт резервные копии" "Backend component"
        }

        aiModel = softwareSystem "Модель генерации" "Создаёт варианты рецептов" {
            tags "External"
        }

        fileStorage = softwareSystem "Хранилище отчётов" "Хранит PDF, XLSX и CSV" {
            tags "External"
        }

        user -> grsn "Использует функции питания" "HTTPS"
        admin -> grsn "Администрирует систему" "HTTPS"
        grsn -> aiModel "Запрашивает рецепт" "API"
        grsn -> fileStorage "Экспортирует отчёты" "PDF/XLSX/CSV"

        user -> grsn.web "Использует" "HTTPS"
        admin -> grsn.web "Администрирует" "HTTPS"
        grsn.web -> grsn.api "Вызывает" "JSON/HTTPS"
        grsn.api -> grsn.db "Читает и пишет" "SQL"
        grsn.api -> aiModel "Генерирует рецепт" "API"
        grsn.api -> grsn.exporter "Передаёт отчёт"
        grsn.exporter -> fileStorage "Сохраняет файл"
        grsn.api -> grsn.backup "Запускает backup"
        grsn.backup -> grsn.db "Считывает данные" "SQL"

        grsn.web -> grsn.api.router "Вызывает REST API" "JSON/HTTPS"
        grsn.api.router -> grsn.api.auth "/auth"
        grsn.api.router -> grsn.api.profile "/profile"
        grsn.api.router -> grsn.api.restrictions "/restrictions"
        grsn.api.router -> grsn.api.ingredients "/ingredients"
        grsn.api.router -> grsn.api.recipe "/recipes/generate"
        grsn.api.router -> grsn.api.history "/recipes"
        grsn.api.router -> grsn.api.reports "/reports"
        grsn.api.router -> grsn.api.analysis "/analysis"
        grsn.api.router -> grsn.api.adminService "/admin"

        grsn.api.auth -> grsn.db "Пользователи и пароли" "SQL"
        grsn.api.profile -> grsn.db "Профили и цели" "SQL"
        grsn.api.restrictions -> grsn.db "Запреты и аллергены" "SQL"
        grsn.api.ingredients -> grsn.db "Каталог ингредиентов" "SQL"
        grsn.api.recipe -> grsn.db "Данные генерации" "SQL"
        grsn.api.recipe -> aiModel "Контекст рецепта" "API"
        grsn.api.history -> grsn.db "Рецепты и оценки" "SQL"
        grsn.api.reports -> grsn.db "nutrition_reports" "SQL"
        grsn.api.reports -> fileStorage "PDF, XLSX, CSV"
        grsn.api.analysis -> grsn.db "Профиль и история" "SQL"
        grsn.api.adminService -> grsn.db "Справочники и логи" "SQL"
    }

    views {
        systemContext grsn "C4_Context_AS_GRSN" {
            title "Контекстная C4-модель АС ГРСН"
            include user
            include admin
            include grsn
            include aiModel
            include fileStorage
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
            autolayout tb
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
