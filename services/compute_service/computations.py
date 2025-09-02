from abc import ABC, abstractmethod

class StatefulComputation(ABC):
    """
    Abstract base class for stateful computations.
    """
    @abstractmethod
    def update(self, value: float, timestamp: float) -> float:
        """
        Update the computation with a new value and timestamp.
        Returns the new computed value.
        """
        pass

class RunningAverage(StatefulComputation):
    """
    Computes a running (cumulative) average.
    """
    def __init__(self):
        self.count = 0
        self.sum = 0.0

    def update(self, value: float, timestamp: float) -> float:
        self.count += 1
        self.sum += value
        return self.sum / self.count if self.count > 0 else 0.0

class Integrator(StatefulComputation):
    """
    Computes the integral of a signal over time using the trapezoidal rule.
    """
    def __init__(self):
        self.last_value = None
        self.last_timestamp = None
        self.integral = 0.0

    def update(self, value: float, timestamp: float) -> float:
        if self.last_timestamp is not None:
            dt = timestamp - self.last_timestamp
            if dt > 0:
                # Add the area of the trapezoid
                self.integral += (value + self.last_value) / 2.0 * dt

        self.last_value = value
        self.last_timestamp = timestamp
        return self.integral

class Differentiator(StatefulComputation):
    """
    Computes the derivative of a signal with respect to time.
    """
    def __init__(self):
        self.last_value = None
        self.last_timestamp = None

    def update(self, value: float, timestamp: float) -> float:
        derivative = 0.0
        if self.last_timestamp is not None:
            dt = timestamp - self.last_timestamp
            if dt > 0:
                dv = value - self.last_value
                derivative = dv / dt

        self.last_value = value
        self.last_timestamp = timestamp
        return derivative
