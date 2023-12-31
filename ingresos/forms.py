from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, ValidationError, Email
from wtforms.fields import StringField, IntegerField, DateField, SubmitField, SelectField, PasswordField, FormField, FieldList
from flask_wtf.file import FileField, FileRequired, FileAllowed
from datetime import datetime

# todo Crear validadores para revisar que el nit esté registardo



class JobDate:
    """
    This validator will check if a job en programed in the past
    meaning prior to current day
    """
    def __init__(self, message=None):
        self.message = None

    def __call__(self, form, field):
        if field.data >= datetime.now().date():
            return
        if self.message is None:
            self.message = "Los trabajos no se pueden agendar en fechas pasadas"
        raise ValidationError(self.message)


class ParafiscalesDate:
    """esta validador es para checkear que la fecha de los aprafiscales no esté en el pasado"""
    def __init__(self, message=None):
        self.message = None

    def __call__(self, form, field):
        if field.data.month >= datetime.now().month and field.data.year == datetime.now().year:
            return
        if self.message is None:
            self.message = "Los parafiscales no pueden estar en el pasado"
        raise ValidationError(self.message)


class JobEnds:
    """
    This validator will check if a job start date is less than its end date
    meaning prior to current day
    """
    def __init__(self, fieldname, message=None):
        self.message = None
        self.fieldname = fieldname

    def __call__(self, form, field):
        other = form[self.fieldname]
        if field.data >= other.data:
            return
        if self.message is None:
            self.message = f"El trabajo debe terminar en {datetime.now().date()} o después"
        raise ValidationError(self.message)


class RegisterForm(FlaskForm):
    name = StringField(label="Nombre", validators=[DataRequired()])
    nit = StringField(label="NIT", validators=[DataRequired(), Length(min=10, max=10)])
    email = StringField(label="Email", validators=[DataRequired(), Email()])
    password = PasswordField(label="Contraseña", validators=[DataRequired(), Length(6)])
    submit = SubmitField("Registrar")


class LoginForm(FlaskForm):
    nit = StringField(label="NIT", validators=[DataRequired()])
    password = PasswordField(label="Contraseña", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Ingresa")


class WorkerForm(FlaskForm):
    identification = IntegerField(label="Identificación", validators=[DataRequired()])
    id_type = SelectField(label="Tipo de documento", choices=[("CC", "Cédula ciudadanía"), ("PP", "Pasaporte")])
    birth_date = DateField(label="Fecha de nacimiento")
    gender = SelectField(label="Sexo", choices=[("M", "Hombre"), ("F", "Mujer")])
    last_name = StringField(label="Apellido", validators=[DataRequired()])
    first_name = StringField(label="Nombre", validators=[DataRequired()])
    rh = SelectField(label="RH", choices=["+", "-"], validators=[DataRequired()])
    blood_type = SelectField(label="Tipo sangre", choices=["A", "B", "O", "AB"], validators=[DataRequired()])
    residency_state = SelectField(label="Departamento", validators=[DataRequired()], render_kw={"id": "departamentos"})
    residency_city = SelectField(label="Municipio residencia", validators=[DataRequired()], choices=["Bogotá", "Medellín", "Cartagena"], render_kw={"id": "municipios"})
    origin_country = SelectField(label="País de origen", choices=["Colombia", "Otros"], validators=[DataRequired()])
    mobile_phone = IntegerField(label="Teléfono celular", validators=[DataRequired()])
    submit = SubmitField(label="REGISTRAR")


class JobForm(FlaskForm):
    # title = StringField(label="Trabajo")
    assigned_jobs = SelectField(label="Trabajos habilitados", coerce=int)
    venue = SelectField(label="Seleccione sede", coerce=int)
    start_date = DateField(label="Fecha de inicio", validators=[DataRequired(), JobDate()], default=datetime.now().date())
    end_date = DateField(label="Fecha de terminanción", validators=[DataRequired(), JobEnds(fieldname="start_date")], default=datetime.now().date())
    # submit = SubmitField(label="Crear trabajo")


class MultipleJobForm(FlaskForm):
    """this is the multiform form creating several jobs depending on the workers selected"""
    jobs = FieldList(FormField(JobForm), min_entries=1)


class AssignedJobForm(FlaskForm):
    description = StringField(label="Descripción", validators=[DataRequired()])
    supp_id = IntegerField(label="supp_id")
    submit = SubmitField(label="Crear")


class WorkerRequirementsForm(FlaskForm):
    req_date = DateField(label="Fecha de pago", validators=[DataRequired(), ParafiscalesDate()])
    worker_id = IntegerField(label="worker_id")
    radication_number = IntegerField(label="Número de radicación")
    req_doc = FileField(label="Documento", validators=[FileAllowed(["pdf"], "Únicamente PDF")])
    submit = SubmitField(label="Guardar requerimiento")