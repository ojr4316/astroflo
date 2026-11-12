""" Button sources for the UI input loop: simulated buttons (any OS) or the TFT's GPIO buttons. """
import queue
import time

BUTTONS = ("A", "B", "L", "R", "U", "D", "C")


class DisplayButtons:
    """ Physical buttons read through the display (TFT bonnet) """

    simulated = False

    def __init__(self, display):
        self.display = display

    def read_buttons(self, last_input):
        self.display.read_buttons(last_input)


class SimInput:
    """
    Simulated presses/releases/holds of the seven TFT buttons, fed through the same
    `Input.update()` as the real buttons. Thread-safe: events can come from the web server,
    scripts or tests while the UI input loop polls `read_buttons()` every ~10 ms.
    """

    simulated = True

    def __init__(self):
        self.state = {b: False for b in BUTTONS}
        self.events = queue.Queue()
        self._wait_until = 0.0

    @staticmethod
    def _check(button: str) -> str:
        b = button.upper()
        if b not in BUTTONS:
            raise ValueError(f"Unknown button '{button}'. Buttons: {', '.join(BUTTONS)}")
        return b

    # ---------- event producers ----------
    def press(self, button: str):
        self.events.put((self._check(button), True))

    def release(self, button: str):
        self.events.put((self._check(button), False))

    def tap(self, button: str):
        self.press(button)
        self.release(button)

    def hold(self, button: str, seconds: float):
        self.press(button)
        self.wait(seconds)
        self.release(button)

    def wait(self, seconds: float):
        self.events.put(("wait", float(seconds)))

    def run_script(self, script: str):
        """ Space-separated steps: `A` (tap), `+A` (press), `-A` (release), `hold:A:1.5`, `wait:0.5` """
        for step in script.split():
            if step.startswith("wait:"):
                self.wait(float(step.split(":", 1)[1]))
            elif step.startswith("hold:"):
                _, button, seconds = step.split(":")
                self.hold(button, float(seconds))
            elif step.startswith("+"):
                self.press(step[1:])
            elif step.startswith("-"):
                self.release(step[1:])
            else:
                self.tap(step)

    def pending(self) -> int:
        return self.events.qsize()

    # ---------- consumer ----------
    def _apply_next(self, honor_waits: bool):
        if honor_waits and time.monotonic() < self._wait_until:
            return
        try:
            button, value = self.events.get_nowait()
        except queue.Empty:
            return
        if button == "wait":
            if honor_waits:
                self._wait_until = time.monotonic() + value
            return
        self.state[button] = value

    def _update(self, last_input):
        s = self.state
        last_input.update(s["A"], s["B"], s["L"], s["R"], s["U"], s["D"], s["C"])

    def read_buttons(self, last_input):
        """ One poll from the UI input loop: apply at most one event, then report button states """
        self._apply_next(honor_waits=True)
        self._update(last_input)

    def step(self, last_input):
        """ Like read_buttons() but ignores waits (for tests driving the UI without threads) """
        self._apply_next(honor_waits=False)
        self._update(last_input)

    def drain(self, last_input, max_steps: int = 10_000):
        """ Process every queued event immediately (waits ignored) """
        for _ in range(max_steps):
            if self.events.empty():
                break
            self.step(last_input)
