import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(prog="WireframeStudio")
    parser.add_argument("--self-test", action="store_true", help="run a headless check and exit")
    parser.add_argument("--require-models", action="store_true", help="self-test fails if a model is missing")
    parser.add_argument("--log", help="also write self-test output to this file")
    parser.add_argument("images", nargs="*", help="images to open")
    args = parser.parse_args()

    if args.self_test:
        from .selftest import run

        log_file = open(args.log, "w", encoding="utf-8") if args.log else None

        def log(line):
            if sys.stdout:
                print(line, flush=True)
            if log_file:
                log_file.write(line + "\n")
                log_file.flush()

        try:
            return run(args.require_models, log)
        finally:
            if log_file:
                log_file.close()

    from PySide6.QtWidgets import QApplication

    from .engines.registry import build_engines
    from .paths import models_dir, settings_path
    from .settings import Settings
    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Wireframe Studio")
    app.setStyle("Fusion")
    settings = Settings.load(settings_path())
    window = MainWindow(settings, settings_path(), build_engines(models_dir(), lambda: settings))
    window.add_files(args.images)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
