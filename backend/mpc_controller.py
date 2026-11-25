"""Selective model predictive control. Only the chosen device commands are decisions."""

from __future__ import annotations

from .model_defaults import CONTROL_NAMES

POLICY = "full-climate-2x15-v1"
MAX_MOVE = 0.20  # Fraction of actuator range per 15-minute physical interval.


class MpcStopped(RuntimeError):
    """No command was applied and the current plant state is still usable."""


def devices(value):
    if (
        not isinstance(value, list)
        or len(value) > len(CONTROL_NAMES)
        or any(not isinstance(name, str) or name not in CONTROL_NAMES for name in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("mpcDevices must be a list of unique GreenLight equipment names.")
    return tuple(name for name in CONTROL_NAMES if name in value)


class SelectiveMpc:
    """One solver per horizon per run; recorded weather is a perfect-foresight scenario."""

    def __init__(self, selected):
        self.selected = selected
        self.indices = [CONTROL_NAMES.index(name) for name in selected]
        self.solvers = {}

    def _build(self, core, horizon):
        import casadi as ca

        indices = self.indices
        n = len(indices)
        # One move block over the forecast; re-plan from feedback every interval.
        moves = ca.MX.sym("moves", n)
        # Initial state, native weather rows, same-step rules, last applied moves, targets.
        offset = 28 + 10 * horizon
        data = ca.MX.sym("context", offset + 6 + n + 4)
        state, rules = data[:28], data[offset : offset + 6]
        previous, targets = data[offset + 6 : offset + 6 + n], data[-4:]
        physical = ca.DM(core.p)
        cost = 0
        for k in range(horizon):
            chosen = moves
            u = ca.vertcat(
                *(chosen[indices.index(j)] if j in indices else rules[j] for j in range(6))
            )
            weather = data[28 + 10 * k : 28 + 10 * (k + 1)]
            state = core.F(x0=state, u=u, p=ca.vertcat(weather, physical))["xf"]
            temp = state[2]
            # Same pressure/density conventions as the pinned indoor observations.
            rh = 100 * state[15] / (610.78 * ca.exp(17.2694 * temp / (temp + 238.3)))
            co2_ppm = state[0] * 8.3144598 * (temp + 273.15) / (101325 * 0.04401)
            sun = weather[0] > 0
            target = ca.if_else(sun, targets[0], targets[1])
            cost += (
                ((temp - target) / 2) ** 2
                + (ca.fmax(rh - targets[3], 0) / 10) ** 2
                + sun * (ca.fmax(targets[2] - co2_ppm, 0) / 400) ** 2
                + 0.05 * (u[0] ** 2 + u[1] ** 2 + u[4] ** 2)
                + 0.10 * ca.sumsqr(chosen - previous)
                + 0.02 * ca.sumsqr(chosen - rules[indices])
            )
            previous = chosen
        # Forward directions through the same 900 s integrator, not through a surrogate.
        size = n
        grad = ca.vertcat(*(ca.jtimes(cost, moves, ca.DM.eye(size)[:, i]) for i in range(size)))
        return ca.nlpsol(
            "selective_mpc",
            "ipopt",
            {"x": moves, "p": data, "f": cost},
            {
                "grad_f": ca.Function("mpc_gradient", [moves, data], [cost, grad]),
                "ipopt.hessian_approximation": "limited-memory",
                "ipopt.print_level": 0,
                "ipopt.sb": "yes",
                "print_time": False,
                "ipopt.max_iter": 60,
                "ipopt.acceptable_iter": 3,
                "ipopt.max_cpu_time": 12.0,
                "ipopt.tol": 5e-4,
                "ipopt.acceptable_tol": 2e-3,
                "error_on_fail": False,
            },
        )

    def action(self, core, rules, targets, remaining):
        import numpy as np

        t = int(core.timestep)
        horizon = min(2, remaining, len(core.weather_data) - t)
        if horizon < 1:
            raise MpcStopped("No recorded weather remains for the MPC forecast.")
        previous = core.u[self.indices]
        context = np.r_[
            core.x,
            core.weather_data[t : t + horizon].reshape(-1),
            rules,
            previous,
            [targets[k] for k in ("dayTemp", "nightTemp", "co2", "maxRh")],
        ]
        if not np.isfinite(context).all():
            raise MpcStopped("MPC received a non-finite state, control or forecast.")
        try:
            if horizon not in self.solvers:
                self.solvers[horizon] = self._build(core, horizon)
            solver = self.solvers[horizon]
            lower = np.maximum(0.0, previous.astype(float) - MAX_MOVE)
            upper = np.minimum(1.0, previous.astype(float) + MAX_MOVE)
            result = solver(x0=previous, lbx=lower, ubx=upper, p=context)
            stats = solver.stats()
            plan = np.asarray(result["x"]).ravel()
        except RuntimeError as exc:
            raise MpcStopped("IPOPT could not compute a command. No interval was applied.") from exc
        if (
            not stats["success"]
            or not np.isfinite(plan).all()
            or np.any(plan < lower - 1e-7)
            or np.any(plan > upper + 1e-7)
        ):
            raise MpcStopped(f"MPC stopped ({stats['return_status']}). No interval was applied.")
        action = rules.copy()
        action[self.indices] = np.clip(plan, lower, upper)
        return action
