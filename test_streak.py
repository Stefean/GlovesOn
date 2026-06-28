from app import app, db, Workout
from datetime import datetime, timedelta

TEST_USER_ID = 1 

with app.app_context():
    # 1. Clear out old workouts
    Workout.query.filter_by(user_id=TEST_USER_ID).delete()
    db.session.commit()
    
    # 2. Get dates for Today and 2 Days Ago (We skip Yesterday entirely!)
    today = datetime.now()
    two_days_ago = today - timedelta(days=1)
    three_days_ago = today - timedelta(days=2)
    
    # 3. Create a broken chain of workouts
    w1 = Workout(workout_type="Sparring", rounds=6, intensity=8, created_at=today, user_id=TEST_USER_ID)
    # ❌ NOTICE: No workout is created for yesterday!
    w2 = Workout(workout_type="Heavy Bag", rounds=4, intensity=6, created_at=two_days_ago, user_id=TEST_USER_ID)
    w3 = Workout(workout_type="Push Day", rounds=12, intensity=7, created_at=three_days_ago, user_id=TEST_USER_ID)
    
    db.session.add_all([w1, w2, w3])
    db.session.commit()
    
    print("✅ Broken streak data injected! Check your dashboard.")