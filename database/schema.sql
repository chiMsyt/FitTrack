-- =============================================================================
-- FitTrack: Daily Home Exercise Routine System
-- Database Schema — MySQL 9.7.0 LTS
-- =============================================================================

DROP DATABASE IF EXISTS fittrack_db;
CREATE DATABASE fittrack_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fittrack_db;

CREATE TABLE user (
    user_id        INT          NOT NULL AUTO_INCREMENT,
    username       VARCHAR(50)  NOT NULL,
    email          VARCHAR(100) NOT NULL,
    calorie_goal   INT          NOT NULL DEFAULT 2000,
    calorie_mode   ENUM('deficit','surplus') NOT NULL DEFAULT 'deficit',
    surplus_goal   INT              NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_user      PRIMARY KEY (user_id),
    CONSTRAINT uq_username  UNIQUE (username),
    CONSTRAINT uq_email     UNIQUE (email),
    CONSTRAINT chk_cal_goal CHECK (calorie_goal > 0)
);

CREATE TABLE exercise (
    exercise_id   INT          NOT NULL AUTO_INCREMENT,
    user_id       INT          NOT NULL,
    name          VARCHAR(100) NOT NULL,
    exercise_type ENUM('Reps','Duration','Weighted') NOT NULL,
    amount        INT          NOT NULL,
    category      ENUM('Strength','Cardio','Flexibility','Core','Full Body') NOT NULL DEFAULT 'Strength',
    est_calories  INT          NOT NULL,
    target_muscle VARCHAR(100)     NULL,
    scheduled_day ENUM('Mon','Tue','Wed','Thu','Fri','Sat','Sun','Daily') NOT NULL DEFAULT 'Daily',
    notes         VARCHAR(255)     NULL,
    CONSTRAINT pk_exercise     PRIMARY KEY (exercise_id),
    CONSTRAINT fk_ex_user      FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_ex_name_user UNIQUE (user_id, name),
    CONSTRAINT chk_ex_amount   CHECK (amount > 0),
    CONSTRAINT chk_ex_calories CHECK (est_calories > 0)
);

CREATE TABLE daily_log (
    log_id        INT       NOT NULL AUTO_INCREMENT,
    user_id       INT       NOT NULL,
    exercise_id   INT       NOT NULL,
    log_date      DATE      NOT NULL,
    is_completed  TINYINT(1) NOT NULL DEFAULT 0,
    completed_at  DATETIME      NULL,
    CONSTRAINT pk_log          PRIMARY KEY (log_id),
    CONSTRAINT fk_log_user     FOREIGN KEY (user_id)     REFERENCES user(user_id)         ON DELETE CASCADE,
    CONSTRAINT fk_log_exercise FOREIGN KEY (exercise_id) REFERENCES exercise(exercise_id) ON DELETE CASCADE,
    CONSTRAINT uq_log_per_day  UNIQUE (user_id, exercise_id, log_date)
);

CREATE TABLE weight_log (
    wlog_id     INT           NOT NULL AUTO_INCREMENT,
    user_id     INT           NOT NULL,
    exercise_id INT           NOT NULL,
    log_date    DATE          NOT NULL,
    weight_kg   DECIMAL(6,2)  NOT NULL,
    reps        INT           NOT NULL,
    `sets`      INT           NOT NULL DEFAULT 1,
    notes       VARCHAR(255)      NULL,
    CONSTRAINT pk_wlog         PRIMARY KEY (wlog_id),
    CONSTRAINT fk_wlog_user    FOREIGN KEY (user_id)     REFERENCES user(user_id)         ON DELETE CASCADE,
    CONSTRAINT fk_wlog_ex      FOREIGN KEY (exercise_id) REFERENCES exercise(exercise_id) ON DELETE CASCADE,
    CONSTRAINT chk_wlog_weight CHECK (weight_kg > 0),
    CONSTRAINT chk_wlog_reps   CHECK (reps > 0),
    CONSTRAINT chk_wlog_sets   CHECK (`sets` > 0)
);

CREATE TABLE food_entry (
    entry_id      INT          NOT NULL AUTO_INCREMENT,
    user_id       INT          NOT NULL,
    food_name     VARCHAR(150) NOT NULL,
    calories_kcal INT          NOT NULL,
    meal_type     ENUM('Breakfast','Lunch','Dinner','Snack') NOT NULL,
    entry_date    DATE         NOT NULL DEFAULT '2000-01-01',
    CONSTRAINT pk_food      PRIMARY KEY (entry_id),
    CONSTRAINT fk_food_user FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_food_cal CHECK (calories_kcal >= 0)
);

CREATE TABLE streak (
    streak_id        INT  NOT NULL AUTO_INCREMENT,
    user_id          INT  NOT NULL,
    current_streak   INT  NOT NULL DEFAULT 0,
    best_streak      INT  NOT NULL DEFAULT 0,
    last_active_date DATE     NULL,
    CONSTRAINT pk_streak       PRIMARY KEY (streak_id),
    CONSTRAINT fk_streak_user  FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_streak_user  UNIQUE (user_id),
    CONSTRAINT chk_cur_streak  CHECK (current_streak >= 0),
    CONSTRAINT chk_best_streak CHECK (best_streak >= 0)
);

CREATE INDEX idx_exercise_user  ON exercise   (user_id);
CREATE INDEX idx_log_user_date  ON daily_log  (user_id, log_date);
CREATE INDEX idx_log_exercise   ON daily_log  (exercise_id);
CREATE INDEX idx_food_user_date ON food_entry (user_id, entry_date);
CREATE INDEX idx_wlog_user_ex   ON weight_log (user_id, exercise_id);
CREATE INDEX idx_wlog_user_date ON weight_log (user_id, log_date);

CREATE VIEW v_today_routine AS
SELECT e.exercise_id, e.user_id, e.name AS exercise_name, e.exercise_type,
       e.amount, e.category, e.est_calories, e.target_muscle, e.scheduled_day,
       e.notes, COALESCE(dl.is_completed, 0) AS is_completed, dl.completed_at
FROM exercise e
LEFT JOIN daily_log dl ON dl.exercise_id = e.exercise_id
    AND dl.user_id = e.user_id AND dl.log_date = CURRENT_DATE
WHERE e.scheduled_day = 'Daily'
   OR e.scheduled_day = TRIM(DATE_FORMAT(CURRENT_DATE, '%a'));

CREATE VIEW v_daily_calorie_summary AS
SELECT fe.user_id, fe.entry_date, SUM(fe.calories_kcal) AS total_consumed,
       COALESCE(b.total_burned, 0) AS total_burned,
       SUM(fe.calories_kcal) - COALESCE(b.total_burned, 0) AS net_calories
FROM food_entry fe
LEFT JOIN (
    SELECT dl.user_id, dl.log_date, SUM(e.est_calories) AS total_burned
    FROM daily_log dl JOIN exercise e ON e.exercise_id = dl.exercise_id
    WHERE dl.is_completed = 1 GROUP BY dl.user_id, dl.log_date
) b ON b.user_id = fe.user_id AND b.log_date = fe.entry_date
GROUP BY fe.user_id, fe.entry_date;

CREATE VIEW v_weekly_completion AS
SELECT dl.user_id, dl.log_date, TRIM(DATE_FORMAT(dl.log_date,'%a')) AS day_name,
       COUNT(*) AS total_scheduled, SUM(dl.is_completed) AS total_completed,
       ROUND(SUM(dl.is_completed)/COUNT(*)*100,1) AS completion_rate
FROM daily_log dl
WHERE dl.log_date >= DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY)
  AND dl.log_date <= CURRENT_DATE
GROUP BY dl.user_id, dl.log_date;

CREATE VIEW v_exercise_volume_weekly AS
SELECT e.user_id, e.scheduled_day, e.category, COUNT(e.exercise_id) AS exercise_count
FROM exercise e
GROUP BY e.user_id, e.scheduled_day, e.category;

CREATE VIEW v_30day_heatmap AS
SELECT dl.user_id, dl.log_date,
       CASE WHEN SUM(dl.is_completed) > 0 THEN 1 ELSE 0 END AS was_active,
       SUM(dl.is_completed) AS exercises_done
FROM daily_log dl
WHERE dl.log_date >= DATE_SUB(CURRENT_DATE, INTERVAL 29 DAY)
GROUP BY dl.user_id, dl.log_date;

CREATE VIEW v_weight_progress AS
SELECT wl.user_id, wl.exercise_id, e.name AS exercise_name,
       wl.log_date, MAX(wl.weight_kg) AS max_weight_kg,
       SUM(wl.reps * wl.`sets`) AS total_reps, MAX(wl.reps) AS max_reps
FROM weight_log wl JOIN exercise e ON e.exercise_id = wl.exercise_id
GROUP BY wl.user_id, wl.exercise_id, e.name, wl.log_date;

-- Seed data
INSERT INTO user (username, email, calorie_goal, calorie_mode, surplus_goal)
VALUES ('demo_user', 'demo@fittrack.isu.edu', 1800, 'deficit', NULL);

INSERT INTO exercise (user_id, name, exercise_type, amount, category, est_calories, target_muscle, scheduled_day, notes) VALUES
(1,'Bench Press','Weighted',8,'Strength',60,'Chest, Triceps','Mon','Controlled descent'),
(1,'Squats','Weighted',10,'Strength',80,'Legs, Glutes','Mon',NULL),
(1,'Leg Press','Weighted',12,'Strength',70,'Quads, Glutes','Wed',NULL),
(1,'Cable Row','Weighted',10,'Strength',45,'Back, Biceps','Wed','Keep elbows close'),
(1,'Plank Hold','Duration',2,'Core',30,'Core','Daily',NULL),
(1,'Push-ups','Reps',15,'Strength',40,'Chest, Triceps','Daily',NULL),
(1,'Jumping Jacks','Reps',30,'Cardio',50,'Full Body','Tue',NULL),
(1,'Burpees','Reps',10,'Full Body',100,'Full Body','Thu',NULL),
(1,'Hip Bridges','Reps',15,'Strength',30,'Glutes, Lower Back','Fri',NULL);

INSERT INTO daily_log (user_id, exercise_id, log_date, is_completed, completed_at) VALUES
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 6 DAY),1,DATE_SUB(NOW(),INTERVAL 6 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 6 DAY),1,DATE_SUB(NOW(),INTERVAL 6 DAY)),
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 5 DAY),1,DATE_SUB(NOW(),INTERVAL 5 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 5 DAY),1,DATE_SUB(NOW(),INTERVAL 5 DAY)),
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 4 DAY),1,DATE_SUB(NOW(),INTERVAL 4 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 4 DAY),1,DATE_SUB(NOW(),INTERVAL 4 DAY)),
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 3 DAY),1,DATE_SUB(NOW(),INTERVAL 3 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 3 DAY),0,NULL),
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 2 DAY),1,DATE_SUB(NOW(),INTERVAL 2 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 2 DAY),1,DATE_SUB(NOW(),INTERVAL 2 DAY)),
(1,5,DATE_SUB(CURRENT_DATE,INTERVAL 1 DAY),1,DATE_SUB(NOW(),INTERVAL 1 DAY)),
(1,6,DATE_SUB(CURRENT_DATE,INTERVAL 1 DAY),1,DATE_SUB(NOW(),INTERVAL 1 DAY)),
(1,5,CURRENT_DATE,0,NULL),
(1,6,CURRENT_DATE,0,NULL);

INSERT INTO weight_log (user_id, exercise_id, log_date, weight_kg, reps, `sets`) VALUES
(1,1,DATE_SUB(CURRENT_DATE,INTERVAL 35 DAY),20.0,8,3),
(1,1,DATE_SUB(CURRENT_DATE,INTERVAL 28 DAY),25.0,8,3),
(1,1,DATE_SUB(CURRENT_DATE,INTERVAL 21 DAY),30.0,8,3),
(1,1,DATE_SUB(CURRENT_DATE,INTERVAL 14 DAY),35.0,8,3),
(1,1,DATE_SUB(CURRENT_DATE,INTERVAL 7 DAY),40.0,8,3),
(1,3,DATE_SUB(CURRENT_DATE,INTERVAL 35 DAY),50.0,12,3),
(1,3,DATE_SUB(CURRENT_DATE,INTERVAL 28 DAY),70.0,12,3),
(1,3,DATE_SUB(CURRENT_DATE,INTERVAL 21 DAY),90.0,12,3),
(1,3,DATE_SUB(CURRENT_DATE,INTERVAL 14 DAY),110.0,12,3),
(1,3,DATE_SUB(CURRENT_DATE,INTERVAL 7 DAY),130.0,12,3);

INSERT INTO food_entry (user_id, food_name, calories_kcal, meal_type, entry_date) VALUES
(1,'Oatmeal with banana',380,'Breakfast',CURRENT_DATE),
(1,'Grilled chicken and rice',520,'Lunch',CURRENT_DATE),
(1,'Protein shake',180,'Snack',CURRENT_DATE);

INSERT INTO streak (user_id, current_streak, best_streak, last_active_date)
VALUES (1, 6, 6, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY));
