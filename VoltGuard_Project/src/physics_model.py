"""
VoltGuard - Week 1: Baseline Physics Model (SciPy)
----------------------------------------------------
This is the "Physics Engine" foundation described in the project doc.
Week 1 goal: establish a basic, safe baseline model relating pump RPM to
pipeline pressure -- NOT yet wired to live network traffic (that's Week 2).

Model (simplified, but physically grounded):

    A centrifugal pump's affinity laws state that pressure produced by a
    pump scales with the SQUARE of its rotational speed (RPM), for a fixed
    pipe/impeller geometry:

        P(rpm) = P_rated * (rpm / rpm_rated) ** 2

    We also model the pipe's mechanical pressure rating. If the pump's
    output pressure would exceed the pipe's burst-safety threshold, the
    command is physically catastrophic -- regardless of whether it was
    "valid Modbus syntax."

This module exposes `evaluate_command()`, which Week 2 will call directly
from the network bridge once the C++ parser is wired in.
"""

from dataclasses import dataclass

import numpy as np
from scipy import integrate


@dataclass
class PipelineConfig:
    rpm_rated: float = 1750.0       # pump's rated/nameplate RPM
    pressure_rated_psi: float = 45.0  # pressure (psi) produced at rated RPM
    pipe_burst_psi: float = 150.0     # pipe's mechanical failure threshold
    safety_margin: float = 0.8         # trip BEFORE reaching 100% of burst pressure


class PipelinePhysicsEngine:
    """Mock digital-twin of a water treatment pipeline segment."""

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()

    def predict_pressure(self, rpm: float) -> float:
        """
        Affinity-law pressure prediction for a given pump RPM.
        Negative or nonsensical RPM values are treated as measured (0 psi
        floor) since a pump can't produce negative speed physically --
        which itself is a useful anomaly signal upstream.
        """
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

    def simulate_pressure_response(self, rpm: float, duration_s: float = 5.0, steps: int = 100):
        """
        Simulate the pipeline's transient pressure response over time using
        a simple first-order lag ODE (pressure doesn't jump instantly --
        it ramps toward its steady-state value). Useful later for the Qt
        dashboard's "predicted vs actual" real-time graphs (Week 3).

        dP/dt = (P_target - P) / tau
        """
        tau = 0.5  # system time constant (seconds) -- how "sluggish" the pipe is
        p_target = self.predict_pressure(rpm)

        def ode(t, p):
            return (p_target - p[0]) / tau

        t_span = (0, duration_s)
        t_eval = np.linspace(0, duration_s, steps)
        result = integrate.solve_ivp(ode, t_span, y0=[0.0], t_eval=t_eval)

        return result.t, result.y[0]


def _demo():
    engine = PipelinePhysicsEngine()

    print("=== Mid-Project Review sanity checks ===\n")

    test_cases = [500, 1750, 3000, 50000, -100]
    for rpm in test_cases:
        result = engine.evaluate_command(rpm)
        print(f"RPM={rpm:>7} -> predicted={result['predicted_pressure_psi']:>8} psi "
              f"| threshold={result['safety_threshold_psi']} psi "
              f"| verdict={result['verdict']}")

    print("\n=== Transient response demo (rpm=50000, the attack scenario) ===")
    t, p = engine.simulate_pressure_response(rpm=50000, duration_s=3.0, steps=10)
    for ti, pi in zip(t, p):
        print(f"t={ti:.2f}s  pressure={pi:.1f} psi")


if __name__ == "__main__":
    _demo()
