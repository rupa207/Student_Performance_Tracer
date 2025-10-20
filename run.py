from app import create_app

app = create_app()

if __name__ == "__main__":
    # create tables and run
    app.run(debug=True)


#https://chatgpt.com/share/68f11a89-b42c-8000-8429-3ee9021f6dbd
#https://chatgpt.com/share/68f3ca3f-d120-8007-bd0a-3bffb8c9866f

#registration closed ani chuyisthundi kotha teacher register avlante ela ee problem solve chey
#students details view click chesinapudu mundhu select subject then marks type add option undedhi ala ani subjects ki marks add chesevalam next ipudu add chesina kothavi download report pdf then line grapgh undhi 
#and student paka delete option kuda uninadhi now its not there
#bulk data mali same csv file isthe duplicates isthadha mana code
#u messed with my past features while creating new ones please ee above fix chesi ivuu pleasee


#https://chatgpt.com/share/68f3ca3f-d120-8007-bd0a-3bffb8c9866f

#https://chatgpt.com/share/68f4f861-4990-8007-adbb-2475c6936ef0

from extensions import db
from models import User, Student, Grade

with app.app_context():
    db.create_all()
from flask_migrate import Migrate
from extensions import db

migrate = Migrate(app, db)
#https://chatgpt.com/share/68f50295-3850-8000-9170-9d973137d0c2