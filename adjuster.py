from capture.camera import Camera

ADJUST_LIMIT = 5
ADJUST_SIZE = 100_000
MIN_EXPOSURE = 100_000
MAX_EXPOSURE = 5_000_000

class Adjuster:
    def __init__(self, capturer: Camera, exposure: int = 1_000_000):
        self.capturer = capturer
        self.total_fails = 0
        self.recent_fails = 0
        self.recent_successes = 0
        self.total_successes = 0
        self.exposure = exposure

    def adjust(self, up=True):
        self.exposure = max(MIN_EXPOSURE, min(MAX_EXPOSURE, self.exposure + (ADJUST_SIZE if up else -ADJUST_SIZE)))
        #self.capturer.configure(self.exposure)

    def fail(self):
        # End success streak and update total
        self.total_successes += self.recent_successes
        self.recent_successes = 0

        self.recent_fails += 1
        if self.recent_fails >= ADJUST_LIMIT:
            # Fail streak! increase exposure to show more stars
            self.adjust()

    def success(self):
        # End fail streak and update total
        self.total_fails += self.recent_fails
        self.recent_fails = 0

        self.recent_successes += 1
        if self.recent_successes >= ADJUST_LIMIT * 2:
            # Solve Streak! decrease exposure to attempt speed up
            self.adjust(False)