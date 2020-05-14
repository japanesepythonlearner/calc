#calculation_game/__init__.py
from flask import Flask
app = Flask(__name__)
app.config.from_object('calculation_game.config')
import calculation_game.main
