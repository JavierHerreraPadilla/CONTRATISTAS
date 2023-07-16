import datetime
from ingresos import db
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, CheckConstraint, text
from datetime import datetime as dt


class Client(db.Model, UserMixin):
    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    nit = db.Column(db.Integer, nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

    suppliers = db.relationship("Supplier", backref="client", lazy=True)
    venues = db.relationship("ClientVenue", backref="client", lazy=True)

    def __repr__(self):
        return f"Cliente-{self.name}"


class ClientVenue(db.Model):
    __tablename__ = "client_venues"
    id = db.Column(db.Integer, primary_key=True)
    venue_name = db.Column(db.String(100), nullable=False, default="Principal")
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"))

    jobs = db.relationship("Job", backref="client_venue", lazy=True)

    def __repr__(self):
        return f"{self.client.name} {self.venue_name}"


class Supplier(db.Model, UserMixin):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    nit = db.Column(db.Integer, nullable=False, unique=True) # Debe ser unique la combinación de nit y client_id
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    abled = db.Column(db.Boolean, default=True, nullable=False)

    client_id = db.Column(db.Integer, db.ForeignKey("clients.id")) # foreign key to Client

    workers = db.relationship("Worker", backref="supplier", lazy=True) # relationshiop to Worker model
    jobs = db.relationship("Job", backref="supplier", lazy=True)
    assigned_jobs = db.relationship("SupplierAssignedJobs", backref="supplier", lazy=True)

    __table_args__ = (
        UniqueConstraint('nit', 'client_id', name='unique_nit_client_id'),   # pongo que sea única la combinación nit y client_id porque el mismo supplier puede estar registrado en diferentes clients
    )

    def __repr__(self):
        return f"Supp-{self.name}"


class SupplierAssignedJobs(db.Model):
    __tablename__ = "supplier_assigned_jobs"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))

    __table_args__ = (
        UniqueConstraint('supplier_id', 'description', name='unique_supid_description'),
    )

    def __repr__(self):
        return f"{self.description}"


class Worker(db.Model):
    __tablename__ = "workers"
    id = db.Column(db.Integer, primary_key=True)
    identification = db.Column(db.Integer) # número de documento
    id_type = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(2), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    rh = db.Column(db.String(2), nullable=False)
    blood_type = db.Column(db.String(4), nullable=False)
    residency_state = db.Column(db.String(100), nullable=False)
    residency_city = db.Column(db.String(100), nullable=False)
    origin_country = db.Column(db.String(100), nullable=False)
    mobile_phone = db.Column(db.Integer, nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id")) # foreign key to Supplier
    jobs = db.relationship("JobWorker", backref="worker", lazy=True)
    requirements = db.relationship("WorkerRequirements", backref="worker", lazy=True)

    __table_args__ = (
        UniqueConstraint('identification', 'supplier_id', name='unique_worker_supplier'),   # pongo que sea única la combinación nit y client_id porque el mismo supplier puede estar registrado en diferentes clients
    )

    def __repr__(self):
        return f"{self.id} - {self.first_name} {self.last_name} "


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False, default=start_date + datetime.timedelta(days=30))

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    client_venue_id = db.Column(db.Integer, db.ForeignKey("client_venues.id"))

    workers = db.relationship("JobWorker", backref="job", lazy=True)

    def __repr__(self):
        return f"{self.title}"


class JobWorker(db.Model):
    """this table records the id of a worker linked to the id of a job"""
    ___tablename__ = "job_workers"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"))

    def __repr__(self):
        return f"{self.worker}"


class WorkerRequirements(db.Model):
    """Esta tabala debe incluir todos los requerimientos que
    el trabajador debe cumplir para que se le permita hacer trabajos"""
    # TODO: por el momento solo va a incluir el mes de vigencia de los parafiscales
    __tablename__ = "worker_requirements"
    id = db.Column(db.Integer, primary_key=True)
    para_date = db.Column(db.DateTime, nullable=True)
    document = db.Column(db.Text)
    radication_number = db.Column(db.Integer)
    until_date = db.Column(db.DateTime)
    worker_id = db.Column(db.Integer, db.ForeignKey("workers.id"))

    def __repr__(self):
        return f"{self.worker_id} - {self.para_date}"
