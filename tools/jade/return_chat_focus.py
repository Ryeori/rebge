"""Return foreground to the user's ChatGPT/Codex window after game input."""


def return_chat_focus():
    from automation_paths import configure_imports
    configure_imports()
    from um.win import Drive
    errors = []
    for process in ('ChatGPT', 'Codex'):
        driver = None
        try:
            driver = Drive(process)
            driver.focus()
            return dict(returned=True, process=process)
        except Exception as error:
            errors.append(dict(process=process, error=repr(error)))
        finally:
            if driver is not None:
                driver.close()
    return dict(returned=False, errors=errors)


if __name__ == '__main__':
    import json
    print(json.dumps(return_chat_focus()))
