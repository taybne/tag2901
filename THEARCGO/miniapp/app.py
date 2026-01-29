from flask import Flask, render_template, request, jsonify
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flask_admin.contrib import sqla
from datetime import datetime
import json

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-change-it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tag.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===== МОДЕЛИ (ПЕРЕМЕСТИЛ ВВЕРХ!) =====
class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True)  # novosibirsk, moscow

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    city = db.relationship('City', backref='locations')
    theme = db.Column(db.String(50))  # popular, culture
    photos = db.Column(db.Text)  # JSON
    approved = db.Column(db.Boolean, default=False)

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20))  # city или place
    city = db.Column(db.String(100))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    user_id = db.Column(db.String(50))
    nickname = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== АДМИНКА =====
admin = Admin(app, name='THEARCGO Admin')
admin.add_view(sqla.ModelView(City, db.session))
admin.add_view(sqla.ModelView(Location, db.session))
admin.add_view(sqla.ModelView(Suggestion, db.session))  # ← ГЛАВНОЕ!

# ===== API ДЛЯ ФРОНТЕНДА =====
@app.route('/api/suggest', methods=['POST'])
def suggest():
    data = request.json
    suggestion = Suggestion(
        type=data['type'],
        city=data['city'],
        title=data.get('title'),
        description=data.get('description'),
        user_id=data['user_id'],
        nickname=data['nickname']
    )
    db.session.add(suggestion)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/cities')
def get_cities():
    cities = City.query.all()
    return jsonify([{'name': c.name, 'slug': c.slug} for c in cities])

@app.route('/api/locations/<city_slug>')
def get_locations(city_slug):
    city = City.query.filter_by(slug=city_slug).first()
    if not city:
        return jsonify([])
    locations = Location.query.filter_by(city_id=city.id, approved=True).all()
    def _parse_themes(val):
        if not val:
            return ['popular']
        # If stored as JSON array/string, try to parse
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, str):
                return [parsed]
        except Exception:
            # Not JSON — treat as single theme string
            return [val]

    return jsonify([{
        'title': l.title,
        'desc': l.description or '',
        'themes': _parse_themes(l.theme),
        'photos': json.loads(l.photos or '[]')
    } for l in locations])

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000, debug=True)
@app.route('/api/photo-suggest', methods=['POST'])
def photo_suggest():
    files = request.files.getlist('photos')
    location = request.form['location']
    city = request.form['city']
    user_id = request.form['user_id']
    
    os.makedirs('uploads/photos_pending', exist_ok=True)
    
    for file in files:
        if file.filename:
            filename = f"{user_id}_{int(time.time())}_{file.filename}"
            file.save(f"uploads/photos_pending/{filename}")
            
            # Сохраняем в БД
            photo_suggestion = SuggestionPhoto(
                location_title=location,
                city=city,
                filename=filename,
                user_id=user_id,
                status='pending'
            )
            db.session.add(photo_suggestion)
    
    db.session.commit()
    return jsonify({'success': true})
