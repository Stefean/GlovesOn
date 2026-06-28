from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os 
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = "gloveson_key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gloveson.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = "static/profile_pics"

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_pic = db.Column(db.String(150), nullable = False, default="default.png")
    workouts = db.relationship('Workout', backref='owner', lazy=True)

class Workout(db.Model):
    __tablename__ = 'workouts'
    id = db.Column(db.Integer, primary_key=True)
    workout_type = db.Column(db.String(50), nullable=False)
    rounds = db.Column(db.Integer, nullable=False)
    intensity = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_liked = db.Column(db.Boolean, default=False)
    is_disliked = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password needs atleast 8 characters")
            return redirect(url_for("register"))  
        new_user = User(username=username, password=password, profile_pic="default.png")
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("home"))
        else:
            flash("Incorrect username or password")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    all_workouts = Workout.query.filter_by(user_id=session["user_id"]).order_by(Workout.created_at.desc()).all()

    total_rounds = 0
    for workout in all_workouts:
        total_rounds += workout.rounds

    streak = 0
    if all_workouts:
        trained_days = []
        for workout in all_workouts:
            date_obj = workout.created_at.date()
            if date_obj not in trained_days:
                trained_days.append(date_obj)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        if today in trained_days or yesterday in trained_days:
            streak = 1
            for i in range(len(trained_days) - 1):
                if (trained_days[i] - trained_days[i+1]).days == 1:
                    streak += 1
                else:
                    break

    return render_template('index.html', workouts=all_workouts, total_rounds=total_rounds, streak=streak)

@app.route("/delete/<int:workout_id>", methods=["POST"])
def delete_workout(workout_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    workout = Workout.query.get_or_404(workout_id)
    if workout.user_id == session['user_id']:
        db.session.delete(workout)
        db.session.commit()
    return redirect(url_for("home"))

@app.route("/edit_workout/<int:workout_id>", methods=["POST"])
def edit_workout(workout_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    workout = Workout.query.get_or_404(workout_id)

    if workout.user_id != session['user_id']:
        return redirect(url_for('home'))
    
    workout.workout_type = request.form.get('workout_type')
    workout.rounds = int(request.form.get('rounds'))
    workout.intensity = int(request.form.get('intensity'))
    workout.notes = request.form.get('notes')

    db.session.commit()
    return redirect(url_for('home'))

@app.route("/add_workout", methods=["GET", "POST"])
def add_workout():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        workout_type = request.form.get("workout_type")
        rounds = request.form.get("rounds")
        intensity = request.form.get("intensity")
        notes = request.form.get("notes")
        
        new_workout = Workout(
            workout_type=workout_type,
            rounds=int(rounds) if rounds else 0,
            intensity=int(intensity) if intensity else 0,
            notes=notes,
            user_id=session['user_id']
        )
        
        db.session.add(new_workout)
        db.session.commit()
        return redirect(url_for("home"))       
    return render_template("add_workout.html")

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user = User.query.get_or_404(session['user_id'])

    if request.method == "POST":
        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file and file.filename != "":
                filename = secure_filename(f"user_{user.id}_{file.filename}")
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

                user.profile_pic = filename
                db.session.commit()
                return redirect(url_for('profile'))
            
    workouts = Workout.query.filter_by(user_id=user.id).all()
    total_workouts = len(workouts)
    total_rounds = sum(w.rounds for w in workouts)

    max_rpe = max([w.intensity for w in workouts]) if workouts else 0

    return render_template("profile.html", user=user, total_workouts=total_workouts, total_rounds=total_rounds, max_rpe=max_rpe)

@app.route("/like_workout/<int:workout_id>", methods = ["POST", "GET"])
def like_workout(workout_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    workout = Workout.query.get_or_404(workout_id)

    workout.is_liked = not workout.is_liked
    if workout.is_disliked == True:
        workout.is_disliked = False
    db.session.commit()

    return redirect(url_for("home"))

@app.route("/dislike_workout/<int:workout_id>", methods=["POST", "GET"])
def dislike_workout(workout_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    workout = Workout.query.get_or_404(workout_id)

    workout.is_disliked = not workout.is_disliked
    if workout.is_liked == True:
        workout.is_liked = False

    db.session.commit()
    
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)