export class TimedGesture {
  constructor(holdMs = 1500, graceMs = 250) {
    if (holdMs <= 0 || graceMs < 0) {
      throw new RangeError("Invalid gesture timing.");
    }
    this.holdMs = holdMs;
    this.graceMs = graceMs;
    this.reset();
  }

  update(detected, now) {
    if (!Number.isFinite(now)) throw new TypeError("Timestamp must be finite.");
    let triggered = false;

    if (detected) {
      if (this.startedAt === null) {
        this.startedAt = now;
      } else if (this.lostAt !== null) {
        const gap = now - this.lostAt;
        if (gap > this.graceMs) {
          this.reset();
          this.startedAt = now;
        } else {
          this.startedAt += gap;
        }
      }
      this.lastDetectedAt = now;
      this.lostAt = null;
      const heldMs = now - this.startedAt;
      if (!this.triggered && heldMs >= this.holdMs) {
        this.triggered = true;
        triggered = true;
      }
      return {heldMs, triggered};
    }

    if (this.startedAt === null) return {heldMs: 0, triggered: false};
    if (this.lostAt === null) this.lostAt = now;
    if (now - this.lostAt > this.graceMs) {
      this.reset();
      return {heldMs: 0, triggered: false};
    }
    return {heldMs: this.lastDetectedAt - this.startedAt, triggered: false};
  }

  reset() {
    this.startedAt = null;
    this.lastDetectedAt = null;
    this.lostAt = null;
    this.triggered = false;
  }
}

export class SquatRepCounter {
  static UP = "UP";
  static GOING_DOWN = "GOING_DOWN";
  static DOWN = "DOWN";
  static GOING_UP = "GOING_UP";
  static WAITING_FOR_UP = "WAITING_FOR_UP";

  constructor() {
    this.reset();
  }

  update(angle) {
    if (angle === null || angle === undefined) {
      this.state = SquatRepCounter.WAITING_FOR_UP;
      return false;
    }
    if (!Number.isFinite(angle) || angle < 0 || angle > 180) {
      throw new RangeError("Knee angle must be between 0 and 180.");
    }

    if (this.state === SquatRepCounter.WAITING_FOR_UP) {
      if (angle >= 160) this.state = SquatRepCounter.UP;
    } else if (this.state === SquatRepCounter.UP) {
      if (angle < 150) this.state = SquatRepCounter.GOING_DOWN;
    } else if (this.state === SquatRepCounter.GOING_DOWN) {
      if (angle <= 90) this.state = SquatRepCounter.DOWN;
      else if (angle >= 160) this.state = SquatRepCounter.UP;
    } else if (this.state === SquatRepCounter.DOWN) {
      if (angle > 105) this.state = SquatRepCounter.GOING_UP;
    } else if (this.state === SquatRepCounter.GOING_UP) {
      if (angle >= 160) {
        this.state = SquatRepCounter.UP;
        this.count += 1;
        return true;
      }
      if (angle <= 90) this.state = SquatRepCounter.DOWN;
    }
    return false;
  }

  reset() {
    this.state = SquatRepCounter.UP;
    this.count = 0;
  }
}

export class WorkoutFSM {
  constructor({exercises, holdMs = 1500, graceMs = 250} = {}) {
    if (!Array.isArray(exercises) || exercises.length === 0) {
      throw new TypeError("At least one exercise is required.");
    }
    this.exercises = exercises.map(exercise => {
      const sets = exercise?.sets ?? 1;
      const restSeconds = exercise?.rest_seconds ?? exercise?.rest_sec;
      if (!Number.isInteger(sets) || sets < 1 ||
          !Number.isInteger(restSeconds) || restSeconds < 0) {
        throw new RangeError("Exercise sets and rest duration must be valid integers.");
      }
      return {
        name: String(exercise.name || "Bài tập"),
        sets,
        restSeconds,
        targetReps: Number.isInteger(exercise.target_reps) ? exercise.target_reps : null,
        tracksSquat: exercise.tracks_squat === true
      };
    });
    this.holdMs = holdMs;
    this.graceMs = graceMs;
    this.reset();
  }

  get exercise() {
    return this.exercises[this.exerciseIndex];
  }

  update(features, now) {
    const events = [];
    const visible = features.tracked === true;
    this.tracked = visible;
    if (visible) {
      if (this.trackingLostAt !== null &&
          now - this.trackingLostAt > this.graceMs &&
          this.reportedTracking === true) {
        events.push({type: "TRACKING_LOST"});
        this.reportedTracking = false;
      }
      this.trackingLostAt = null;
      if (this.reportedTracking !== true) {
        events.push({type: "TRACKING_RESTORED"});
        this.reportedTracking = true;
      }
    } else {
      if (this.trackingLostAt === null) this.trackingLostAt = now;
      if (now - this.trackingLostAt > this.graceMs) {
        if (this.reportedTracking !== false) {
          events.push({type: "TRACKING_LOST"});
          this.reportedTracking = false;
        }
        this.trackingLostAt = null;
      }
    }

    if (this.phase === "WAITING_FOR_START") {
      const result = this.startGesture.update(visible && features.start_detected, now);
      if (result.triggered) {
        this.phase = "ACTIVE";
        this.repCounter.reset();
        this.stopGesture.reset();
        events.push({
          type: "START_EXERCISE",
          exercise_index: this.exerciseIndex,
          exercise_name: this.exercise.name
        });
      }
    } else if (this.phase === "ACTIVE") {
      if (this.exercise.tracksSquat && this.repCounter.update(
        visible ? features.knee_angle : null
      )) {
        events.push({
          type: "REP_COMPLETED",
          exercise_index: this.exerciseIndex,
          set_number: this.setNumber,
          rep_count: this.repCounter.count
        });
      }

      const stop = this.stopGesture.update(
        visible && features.x_detected && features.head_visible,
        now
      );
      if (stop.triggered) {
        this.phase = "RESTING";
        this.restEndsAt = now + this.exercise.restSeconds * 1000;
        events.push({
          type: "END_SET",
          exercise_index: this.exerciseIndex,
          exercise_name: this.exercise.name,
          set_number: this.setNumber,
          reps: this.repCounter.count,
          target_reps: this.exercise.targetReps,
          rest_seconds: this.exercise.restSeconds
        });
      }
    } else if (this.phase === "RESTING" && now >= this.restEndsAt) {
      this.restEndsAt = null;
      if (this.setNumber < this.exercise.sets) {
        this.setNumber += 1;
        this.repCounter.reset();
        this.stopGesture.reset();
        this.phase = "ACTIVE";
        events.push({
          type: "REST_COMPLETE",
          exercise_index: this.exerciseIndex,
          set_number: this.setNumber
        });
      } else if (this.exerciseIndex + 1 < this.exercises.length) {
        this.exerciseIndex += 1;
        this.setNumber = 1;
        this.repCounter.reset();
        this.stopGesture.reset();
        this.startGesture.reset();
        this.phase = "WAITING_FOR_START";
        events.push({
          type: "REST_COMPLETE",
          exercise_index: this.exerciseIndex,
          set_number: this.setNumber
        }, {
          type: "EXERCISE_READY",
          exercise_index: this.exerciseIndex,
          exercise_name: this.exercise.name
        });
      } else {
        this.phase = "COMPLETE";
        events.push({type: "WORKOUT_COMPLETE"});
      }
    }

    return {events, view: this.view(now)};
  }

  view(now) {
    const restRemaining = this.restEndsAt === null
      ? 0 : Math.max(0, (this.restEndsAt - now) / 1000);
    return {
      phase: this.phase,
      exercise_index: this.exerciseIndex,
      exercise_name: this.exercise.name,
      set_number: this.setNumber,
      sets_total: this.exercise.sets,
      reps: this.repCounter.count,
      target_reps: this.exercise.targetReps,
      tracking: this.tracked,
      rest_remaining_seconds: restRemaining,
      start_progress: this.startGesture.progress(now),
      stop_progress: this.stopGesture.progress(now),
      rep_state: this.repCounter.state
    };
  }

  reset() {
    this.phase = "WAITING_FOR_START";
    this.exerciseIndex = 0;
    this.setNumber = 1;
    this.tracked = false;
    this.reportedTracking = null;
    this.trackingLostAt = null;
    this.restEndsAt = null;
    this.startGesture = new TimedGesture(this.holdMs, this.graceMs);
    this.stopGesture = new TimedGesture(this.holdMs, this.graceMs);
    this.repCounter = new SquatRepCounter();
  }
}

TimedGesture.prototype.progress = function(now) {
  if (this.startedAt === null) return 0;
  const heldMs = this.lostAt === null
    ? now - this.startedAt
    : this.lastDetectedAt - this.startedAt;
  return Math.min(1, heldMs / this.holdMs);
};
