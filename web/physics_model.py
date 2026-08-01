"""
VoltGuard (Web) - Physics Engine
--------------------------------
Same physics model as the Week 1 desktop prototype (physics_model.py),
unchanged in substance. This is the "digital twin" that predicts pipeline
pressure from a requested pump RPM, using the pump affinity law:

    P(rpm) = P_rated * (rpm / rpm_rated) ** 2

A command is CATASTROPHIC if the predicted pressure would exceed the
pipe's safety-margined burst threshold, regardless of whether the network
packet that carried it was syntactically valid.
"""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    rpm_rated: float = 1750.0          # pump's rated/nameplate RPM
    pressure_rated_psi: float = 45.0   # pressure (psi) produced at rated RPM
    pipe_burst_psi: float = 150.0      # pipe's mechanical failure threshold
    safety_margin: float = 0.8         # trip BEFORE reaching 100% of burst pressure


class PipelinePhysicsEngine:
    """Mock digital-twin of a water treatment pipeline segment."""

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()

    def predict_pressure(self, rpm: float) -> float:
        """Affinity-law pressure prediction for a given pump RPM."""
        if rpm <= 0:
            return 0.0
        cfg = self.config
        return cfg.pressure_rated_psi * (rpm / cfg.rpm_rated) ** 2

    def safety_threshold_psi(self) -> float:
        cfg = self.config
        return cfg.pipe_burst_psi * cfg.safety_margin

    def evaluate_command(self, rpm: float) -> dict:
        """
        Run a requested RPM setpoint through the physics model and
        classify it as SAFE or CATASTROPHIC.
        """
        predicted_psi = self.predict_pressure(rpm)
        threshold_psi = self.safety_threshold_psi()
        is_catastrophic = predicted_psi > threshold_psi or rpm < 0

        return {
            "requested_rpm": rpm,
            "predicted_pressure_psi": round(predicted_psi, 2),
            "safety_threshold_psi": round(threshold_psi, 2),
            "verdict": "CATASTROPHIC" if is_catastrophic else "SAFE",
        }
