-- =============================================================================
-- FitTrack: Daily Home Exercise Routine System
-- Database Schema — MySQL 9.7.0 LTS
-- DSA-221: Information Management | Final Project
--
-- Structure:
--   1. Schema setup
--   2. Table definitions (normalized to 3NF)
--   3. Indexes
--   4. Views (for dashboard queries)
--   5. Seed data (demo user + sample records)
-- =============================================================================

DROP DATABASE IF EXISTS fittrack_db;
CREATE DATABASE fittrack_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE fittrack_db;

-- =============================================================================
-- TABLE: user
-- One record per registered user.
-- All other tables reference this via user_id (FK).
-- =============================================================================
CREATE TABLE user (
    user_id       INT            NOT NULL AUTO_INCREMENT,
    username      VARCHAR(50)    NOT NULL,
    email         VARCHAR(100)   NOT NULL,
    calorie_goal  INT            NOT NULL DEFAULT 2000,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_user         PRIMARY KEY (user_id),
    CONSTRAINT uq_username     UNIQUE (username),
    CONSTRAINT uq_email        UNIQUE (email),
    CONSTRAINT chk_cal_goal    CHECK (calorie_goal > 0)
);

-- =============================================================================
-- TABLE: exercise
-- The user's personal exercise library.
-- Each exercise belongs to exactly one user.
-- est_calories is set explicitly by the user (BR-05, 3NF: not derived from difficulty).
-- =============================================================================
CREATE TABLE exercise (
    exercise_id   INT            NOT NULL AUTO_INCREMENT,
    user_id       INT            NOT NULL,
    name          VARCHAR(100)   NOT NULL,
    exercise_type ENUM('Reps', 'Duration') NOT NULL,
    amount        INT            NOT NULL,
    difficulty    ENUM('Easy', 'Medium', 'Hard') NOT NULL,
    est_calories  INT            NOT NULL,
    target_muscle VARCHAR(100)       NULL,
    scheduled_day ENUM('Mon','Tue','Wed','Thu','Fri','Sat','Sun','Daily') NOT NULL DEFAULT 'Daily',

    CONSTRAINT pk_exercise       PRIMARY KEY (exercise_id),
    CONSTRAINT fk_ex_user        FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_ex_name_user   UNIQUE (user_id, name),           -- BR-01: unique name per user
    CONSTRAINT chk_ex_amount     CHECK (amount > 0),               -- BR-03
    CONSTRAINT chk_ex_calories   CHECK (est_calories > 0)          -- BR-05
);

-- =============================================================================
-- TABLE: daily_log
-- One row per exercise per day.
-- Tracks whether the exercise was completed and when.
-- is_completed uses TINYINT(1) as MySQL boolean.
-- =============================================================================
CREATE TABLE daily_log (
    log_id        INT            NOT NULL AUTO_INCREMENT,
    user_id       INT            NOT NULL,
    exercise_id   INT            NOT NULL,
    log_date      DATE           NOT NULL,
    is_completed  TINYINT(1)     NOT NULL DEFAULT 0,
    completed_at  DATETIME           NULL,

    CONSTRAINT pk_log            PRIMARY KEY (log_id),
    CONSTRAINT fk_log_user       FOREIGN KEY (user_id)     REFERENCES user(user_id)     ON DELETE CASCADE,
    CONSTRAINT fk_log_exercise   FOREIGN KEY (exercise_id) REFERENCES exercise(exercise_id) ON DELETE CASCADE,
    CONSTRAINT uq_log_per_day    UNIQUE (user_id, exercise_id, log_date) -- BR-09: no duplicates per day
    -- BR-08 (no future dates) enforced at application layer;
    -- MySQL disallows non-deterministic functions (CURRENT_DATE) in CHECK constraints.
);

-- =============================================================================
-- TABLE: food_entry
-- Nutritional intake log per user per day.
-- calories_kcal >= 0 allows zero-calorie entries (e.g., water) per BR-12.
-- =============================================================================
CREATE TABLE food_entry (
    entry_id      INT            NOT NULL AUTO_INCREMENT,
    user_id       INT            NOT NULL,
    food_name     VARCHAR(150)   NOT NULL,
    calories_kcal INT            NOT NULL,
    meal_type     ENUM('Breakfast', 'Lunch', 'Dinner', 'Snack') NOT NULL,
    entry_date    DATE           NOT NULL DEFAULT (CURRENT_DATE),

    CONSTRAINT pk_food           PRIMARY KEY (entry_id),
    CONSTRAINT fk_food_user      FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_food_cal      CHECK (calories_kcal >= 0)  -- BR-12
);

-- =============================================================================
-- TABLE: streak
-- One row per user (1:1 with user).
-- Stores current and best streak — not derived on every query (performance).
-- last_active_date drives the streak increment/reset logic in the app layer.
-- =============================================================================
CREATE TABLE streak (
    streak_id        INT   NOT NULL AUTO_INCREMENT,
    user_id          INT   NOT NULL,
    current_streak   INT   NOT NULL DEFAULT 0,
    best_streak      INT   NOT NULL DEFAULT 0,
    last_active_date DATE      NULL,

    CONSTRAINT pk_streak         PRIMARY KEY (streak_id),
    CONSTRAINT fk_streak_user    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_streak_user    UNIQUE (user_id),             -- BR-16: exactly one record per user
    CONSTRAINT chk_cur_streak    CHECK (current_streak >= 0),
    CONSTRAINT chk_best_streak   CHECK (best_streak >= 0)
);

-- =============================================================================
-- INDEXES
-- Beyond the PKs and UQs above (which auto-create indexes),
-- these cover the most common query patterns.
-- =============================================================================

-- Exercise queries filtered by user
CREATE INDEX idx_exercise_user
    ON exercise (user_id);

-- Log queries filtered by user + date (dashboard today view, progress heatmap)
CREATE INDEX idx_log_user_date
    ON daily_log (user_id, log_date);

-- Log queries filtered by exercise (cascade checks, per-exercise history)
CREATE INDEX idx_log_exercise
    ON daily_log (exercise_id);

-- Food queries filtered by user + date (daily calorie totals)
CREATE INDEX idx_food_user_date
    ON food_entry (user_id, entry_date);

-- =============================================================================
-- VIEWS
-- Pre-built query templates used by the dashboard and progress pages.
-- The application layer calls these views; raw table logic stays here.
-- =============================================================================

-- v_today_routine: exercises scheduled for today + their completion status
CREATE VIEW v_today_routine AS
SELECT
    e.exercise_id,
    e.user_id,
    e.name                              AS exercise_name,
    e.exercise_type,
    e.amount,
    e.difficulty,
    e.est_calories,
    e.target_muscle,
    e.scheduled_day,
    COALESCE(dl.is_completed, 0)        AS is_completed,
    dl.completed_at
FROM exercise e
LEFT JOIN daily_log dl
    ON  dl.exercise_id = e.exercise_id
    AND dl.user_id     = e.user_id
    AND dl.log_date    = CURRENT_DATE
WHERE e.scheduled_day = 'Daily'
   OR e.scheduled_day = TRIM(DATE_FORMAT(CURRENT_DATE, '%a'));

-- v_daily_calorie_summary: consumed vs burned per user per date
CREATE VIEW v_daily_calorie_summary AS
SELECT
    fe.user_id,
    fe.entry_date,
    SUM(fe.calories_kcal)               AS total_consumed,
    COALESCE(burned.total_burned, 0)    AS total_burned,
    SUM(fe.calories_kcal)
        - COALESCE(burned.total_burned, 0) AS net_calories
FROM food_entry fe
LEFT JOIN (
    SELECT
        dl.user_id,
        dl.log_date,
        SUM(e.est_calories)             AS total_burned
    FROM daily_log dl
    JOIN exercise e ON e.exercise_id = dl.exercise_id
    WHERE dl.is_completed = 1
    GROUP BY dl.user_id, dl.log_date
) burned
    ON  burned.user_id   = fe.user_id
    AND burned.log_date  = fe.entry_date
GROUP BY fe.user_id, fe.entry_date;

-- v_weekly_completion: completion rate per day of week for current week
CREATE VIEW v_weekly_completion AS
SELECT
    dl.user_id,
    dl.log_date,
    TRIM(DATE_FORMAT(dl.log_date, '%a'))        AS day_name,
    COUNT(*)                                     AS total_scheduled,
    SUM(dl.is_completed)                         AS total_completed,
    ROUND(SUM(dl.is_completed) / COUNT(*) * 100, 1) AS completion_rate
FROM daily_log dl
WHERE dl.log_date >= DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY)
  AND dl.log_date <= CURRENT_DATE
GROUP BY dl.user_id, dl.log_date;

-- v_exercise_volume_weekly: how many exercises per day (for weekly planner chart)
CREATE VIEW v_exercise_volume_weekly AS
SELECT
    e.user_id,
    e.scheduled_day,
    COUNT(e.exercise_id) AS exercise_count
FROM exercise e
GROUP BY e.user_id, e.scheduled_day;

-- v_30day_heatmap: one row per day for the last 30 days, with activity flag
CREATE VIEW v_30day_heatmap AS
SELECT
    dl.user_id,
    dl.log_date,
    CASE WHEN SUM(dl.is_completed) > 0 THEN 1 ELSE 0 END AS was_active,
    SUM(dl.is_completed)                                   AS exercises_done
FROM daily_log dl
WHERE dl.log_date >= DATE_SUB(CURRENT_DATE, INTERVAL 29 DAY)
GROUP BY dl.user_id, dl.log_date;

-- =============================================================================
-- SEED DATA
-- Demo user + sample exercises, logs, food entries, and streak record.
-- Provides a working dataset on first launch.
-- =============================================================================

-- Demo user
INSERT INTO user (username, email, calorie_goal)
VALUES ('demo_user', 'demo@fittrack.isu.edu', 2000);

-- Exercises (user_id = 1)
INSERT INTO exercise (user_id, name, exercise_type, amount, difficulty, est_calories, target_muscle, scheduled_day)
VALUES
    (1, 'Push-ups',        'Reps',     15, 'Medium', 40,  'Chest, Triceps',    'Daily'),
    (1, 'Squats',          'Reps',     20, 'Easy',   60,  'Legs, Glutes',      'Daily'),
    (1, 'Plank Hold',      'Duration',  2, 'Medium', 30,  'Core',              'Daily'),
    (1, 'Jumping Jacks',   'Reps',     30, 'Easy',   50,  'Full Body',         'Mon'),
    (1, 'Burpees',         'Reps',     10, 'Hard',   100, 'Full Body',         'Wed'),
    (1, 'Lunges',          'Reps',     16, 'Easy',   55,  'Legs',              'Tue'),
    (1, 'Mountain Climbers','Reps',    20, 'Medium', 70,  'Core, Shoulders',   'Thu'),
    (1, 'Tricep Dips',     'Reps',     12, 'Medium', 35,  'Triceps',           'Fri'),
    (1, 'Hip Bridges',     'Reps',     15, 'Easy',   30,  'Glutes, Lower Back','Sat');

-- Daily log entries — past 7 days (simulates a week of activity)
INSERT INTO daily_log (user_id, exercise_id, log_date, is_completed, completed_at)
VALUES
    -- 6 days ago
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY), 1, DATE_SUB(NOW(), INTERVAL 6 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY), 1, DATE_SUB(NOW(), INTERVAL 6 DAY)),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY), 1, DATE_SUB(NOW(), INTERVAL 6 DAY)),
    -- 5 days ago
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 5 DAY), 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 5 DAY), 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 5 DAY), 0, NULL),
    -- 4 days ago
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 4 DAY), 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 4 DAY), 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 4 DAY), 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
    -- 3 days ago
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 3 DAY), 1, DATE_SUB(NOW(), INTERVAL 3 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 3 DAY), 0, NULL),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 3 DAY), 1, DATE_SUB(NOW(), INTERVAL 3 DAY)),
    -- 2 days ago
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY), 1, DATE_SUB(NOW(), INTERVAL 2 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY), 1, DATE_SUB(NOW(), INTERVAL 2 DAY)),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY), 1, DATE_SUB(NOW(), INTERVAL 2 DAY)),
    -- yesterday
    (1, 1, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), 1, DATE_SUB(NOW(), INTERVAL 1 DAY)),
    (1, 2, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), 1, DATE_SUB(NOW(), INTERVAL 1 DAY)),
    (1, 3, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), 1, DATE_SUB(NOW(), INTERVAL 1 DAY)),
    -- today (pending)
    (1, 1, CURRENT_DATE, 0, NULL),
    (1, 2, CURRENT_DATE, 0, NULL),
    (1, 3, CURRENT_DATE, 0, NULL);

-- Food entries (today)
INSERT INTO food_entry (user_id, food_name, calories_kcal, meal_type, entry_date)
VALUES
    (1, 'Oatmeal with banana',      380, 'Breakfast', CURRENT_DATE),
    (1, 'Grilled chicken and rice', 520, 'Lunch',     CURRENT_DATE),
    (1, 'Protein shake',            180, 'Snack',     CURRENT_DATE);

-- Streak record
INSERT INTO streak (user_id, current_streak, best_streak, last_active_date)
VALUES (1, 7, 7, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY));

-- =============================================================================
-- QUICK VERIFICATION QUERIES (comment out before production use)
-- =============================================================================
-- SELECT * FROM v_today_routine WHERE user_id = 1;
-- SELECT * FROM v_daily_calorie_summary WHERE user_id = 1 AND entry_date = CURRENT_DATE;
-- SELECT * FROM v_weekly_completion WHERE user_id = 1;
-- SELECT * FROM v_30day_heatmap WHERE user_id = 1;
