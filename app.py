import numpy as np
import pandas as pd
import datetime as dt

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from flask import Flask, jsonify

# Database Setup
database_path = "./Resources/hawaii.sqlite"
engine = create_engine(f"sqlite:///{database_path}", echo=False)

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(engine, reflect=True)

# Save reference to the table
Measurements = Base.classes.measurement
Stations = Base.classes.station

# Flask Setup
app = Flask(__name__)


# Flask Routes

@app.route("/")
def welcome():
    """List all available api routes."""
    return (
        f"Available Routes:<br/>"
        f"/api/v1.0/precipitation<br/>"
        f"/api/v1.0/stations</br>"
        f"/api/v1.0/tobs<br/>"
        f"/api/v1.0/precipitation"
    )

@app.route("/api/v1.0/precipitation")
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query precipitation data
    
    query_date = dt.date(2017, 8, 23) - dt.timedelta(days=365)
    precipScores = session.query(Measurements.station, Measurements.date, Measurements.prcp).filter(Measurements.date >= query_date).\
    order_by(Measurements.date).all()
    session.close()

    
    prcpScores_df = pd.DataFrame(precipScores, columns=['Stations','Date','Precipitation'])
    prcpSums_df = prcpScores_df.groupby("Date").sum()
    


    # Convert list of tuples into normal list
    prcpData = [prcpSums_df.to_dict()]
    
    return jsonify(prcpData)



if __name__ == '__main__':
    app.run(debug=True)