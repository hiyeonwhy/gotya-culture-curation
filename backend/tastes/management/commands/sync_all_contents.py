from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "정제된 취향 질문, 영화, 도서, 문화 데이터를 순서대로 DB에 동기화합니다."

    def add_arguments(self, parser):
        parser.add_argument("--skip-tastes", action="store_true")
        parser.add_argument("--skip-movies", action="store_true")
        parser.add_argument("--skip-books", action="store_true")
        parser.add_argument("--skip-cultures", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        tasks = (
            ("취향 질문", "sync_taste_config", options["skip_tastes"]),
            ("영화", "sync_movies", options["skip_movies"]),
            ("도서", "sync_books", options["skip_books"]),
            ("문화", "sync_cultures", options["skip_cultures"]),
        )

        for label, command_name, should_skip in tasks:
            if should_skip:
                self.stdout.write(self.style.WARNING(f"{label} 동기화를 건너뜁니다."))
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{label} 동기화 시작]"))
            call_command(command_name)
            if command_name == "sync_taste_config":
                self.stdout.write(self.style.SUCCESS("[취향 질문 동기화 완료]"))

        self.stdout.write(self.style.SUCCESS("전체 콘텐츠 동기화가 완료되었습니다."))
