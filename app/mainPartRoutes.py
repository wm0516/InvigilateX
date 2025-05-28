from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app import app
import os
from io import BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
from .backend import *
from .database import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()






# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_user_data():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return {
                'user_id': user_id,
                'user_name': user.username,
                'user_department': user.department,
                'user_email': user.email,
                'user_contact': user.contact
            }
    return {
        'user_id': None,
        'user_name': '',
        'user_department': '',
        'user_email': '',
        'user_contact': ''
    }


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/home', methods=['GET', 'POST'])
def homepage():
    return render_template('mainPart/homepage.html', active_tab='home')

@app.route('/home/autoGenerate', methods=['GET', 'POST'])
def auto_generate():
    if request.method == 'POST':
        flash(f"{request.method}")
        flash(f"{request.files}")
        flash(f"{request.form}")
    return render_template('mainPart/generateSchedule.html', active_tab='autoGenerate')

@app.route('/home/manageLecturer')
def manage_lecturer():
    return render_template('mainPart/manageLecturer.html', active_tab='manage')



@app.route('/home/upload')
def upload():
    return render_template('mainPart/upload.html', active_tab='upload')







UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@app.route('/home/uploadLecturerTimetable', methods=['GET', 'POST'])
def upload_lecturer_timetable():
    if request.method == 'POST':
        #flash(f"{request.method}")
        #flash(f"{request.files}")
        #flash(f"{request.form}")

        if 'lecturer_file' not in request.files:
            flash('No file part')
            return jsonify({'error': 'No file part in the request'}), 400

        file = request.files['lecturer_file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file.filename is None:
            return jsonify({'error': 'Filename is missing.'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            return jsonify({
                'message': 'Lecturer timetable file uploaded and read successfully!',
                'columns': df.columns.tolist(),
                'preview': df.head(3).to_dict(orient='records')
            })
        except Exception as e:
            return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500

    return render_template('mainPart/uploadLecturerTimetable.html', active_tab='uploadLecturerTimetable')









@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    if request.method == 'POST':

        if 'exam_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['exam_file']
        file_stream = BytesIO(file.read())
        records_added = 0
        errors = []
        warnings = []

        try:
            excel_file = pd.ExcelFile(file_stream)
            
            for sheet_name in excel_file.sheet_names:
                current_app.logger.info(f"Processing sheet: {sheet_name}")

                try:
                    # ✅ Only reads columns A to I, skips the first row (headers start from row 2)
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols="A:I",
                        skiprows=1
                    )

                    # ✅ Assign expected column names
                    df.columns = ['Date', 'Day', 'Start', 'End', 'Program', 'Course/Sec', 'Lecturer', 'No Of', 'Room']

                    # ➕ You can add further logic to insert or process the data here.
                    records_added += len(df)

                except Exception as e:
                    error_msg = f"Error processing sheet '{sheet_name}': {str(e)}"
                    errors.append(error_msg)
                    current_app.logger.error(error_msg)
                    continue

            response_data = {
                'success': True,
                'message': f'Successfully processed {records_added} record(s).'
            }

            if warnings:
                response_data['warnings'] = warnings
            if errors:
                response_data['errors'] = errors

            return jsonify(response_data)

        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            current_app.logger.error(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
        
    return render_template('mainPart/uploadExamDetails.html', active_tab='uploadLecturerTimetable')

        



'''
@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    exam_data = ''
    if request.method == 'POST':
        #flash(f"{request.method}")
        #flash(f"{request.files}")
        #flash(f"{request.form}")
        #flash(f"Files keys: {list(request.files.keys())}")
        if 'exam_file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        file = request.files['exam_file']
        try:
            excel_file = pd.ExcelFile(file)

            for sheet_name in excel_file.sheet_names:
                current_app.logger.info(f"Processing sheet: {sheet_name}")
                department_code = sheet_name.strip().upper()
            pass
        except:
            pass

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file.filename is None:
            return jsonify({'error': 'Filename is missing.'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            return jsonify({
                'message': 'File uploaded and read successfully!',
                'columns': df.columns.tolist(),
                'preview': df.head(3).to_dict(orient='records')
            })
        except Exception as e:
            return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500
        
    return render_template('mainPart/uploadExamDetails.html', active_tab='uploadExamDetails', exam_data=exam_data)


























@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    exam_data=''
    if request.method == 'POST':
        flash(f"{request.method}")
        flash(f"{request.files}")
        flash(f"{request.form}")
        flash(f"Files keys: {list(request.files.keys())}")
        if 'exam_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['exam_file']
        
        if not file or not file.filename:
            flash('No file selected')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                df = pd.read_excel(filepath)  # Use pd.read_csv() if using .csv files
                exam_data = df.to_dict(orient='records')  # Converts DataFrame to a list of dicts

                print(df.head())  # Debugging
                return "File uploaded and read successfully!"
            except Exception as e:
                flash(f"Error reading Excel file: {e}")
                return redirect(request.url)

        flash('Invalid file type. Only Excel files are supported.')
        return redirect(request.url)

    return render_template('mainPart/uploadExamDetails.html', active_tab='uploadExamDetails', exam_data=exam_data)
'''


'''
if 'exam_file' not in request.files:
    return redirect(request.url)

file = request.files['exam_file']

try:
    excel_file = pd.ExcelFile(file)

    for sheet_name in excel_file.sheet_names:
        current_app.logger.info(f"Processing sheet: {sheet_name}")
        # department_code = sheet_name.strip().upper()

        try:
            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                usecold="A:c"
            )

            df.columns = ['Name', 'Email', 'Level']

        except:
            pass

except:
    pass
'''