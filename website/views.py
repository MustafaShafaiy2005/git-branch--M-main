
from pathlib import Path
from uuid import uuid4
from functools import wraps
from datetime import datetime, timezone
import json

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    jsonify,
    redirect,
    url_for,
    abort,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .models import (
    Note,
    Question,
    MockTest,
    TestAttempt,
    TestAnswer,
)

views = Blueprint('views', __name__)

ALLOWED_IMAGE_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp'
}


# ==========================================
# Administrator access control
# ==========================================

def admin_required(view_function):
    @wraps(view_function)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)

        return view_function(*args, **kwargs)

    return wrapped_view


# ==========================================
# Image upload helper
# ==========================================

def save_question_image():
    """Save an optional image in static/uploads/questions."""
    image = request.files.get('image')

    if not image or not image.filename:
        return None

    original_name = secure_filename(image.filename)

    if (
        not original_name
        or '.' not in original_name
        or original_name.rsplit('.', 1)[1].lower()
        not in ALLOWED_IMAGE_EXTENSIONS
    ):
        raise ValueError(
            'Use a PNG, JPG, JPEG, GIF, or WEBP image.'
        )

    extension = original_name.rsplit('.', 1)[1].lower()
    filename = f'{uuid4().hex}.{extension}'

    upload_folder = (
        Path(current_app.static_folder)
        / 'uploads'
        / 'questions'
    )
    upload_folder.mkdir(parents=True, exist_ok=True)
    image.save(upload_folder / filename)

    return f'uploads/questions/{filename}'


# ==========================================
# Homepage: public landing page / SAT dashboard
# ==========================================

@views.route('/')
def home():
    if current_user.is_authenticated:
        return render_template(
            'sat_dashboard.html',
            user=current_user
        )

    return render_template(
        'landing.html',
        user=current_user
    )


# ==========================================
# SAT dashboard
# ==========================================

@views.route('/sat')
@login_required
def sat_dashboard():
    return render_template(
        'sat_dashboard.html',
        user=current_user
    )


# ==========================================
# JSON filter for answer choices
# ==========================================

@views.app_template_filter('from_json')
def from_json_filter(value):
    try:
        result = json.loads(value or '{}')
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError):
        return {}


# ==========================================
# Full-length test dashboard
# ==========================================

@views.route('/full-length-tests')
@login_required
def full_length_tests():
    bank_questions = Question.query.filter(
        Question.is_active.is_(True),
        Question.question_type == 'question_bank',
        Question.mock_test_id.is_(None),
    )

    rw_count = bank_questions.filter_by(
        section='Reading and Writing'
    ).count()

    math_count = bank_questions.filter_by(
        section='Math'
    ).count()

    total_active_questions = bank_questions.count()

    mock_tests = MockTest.query.filter_by(
        is_active=True
    ).order_by(MockTest.id.asc()).all()

    return render_template(
        'full_length_tests.html',
        user=current_user,
        rw_count=rw_count,
        math_count=math_count,
        total_active_questions=total_active_questions,
        mock_tests=mock_tests,
    )


# ==========================================
# Mock test list
# ==========================================

@views.route('/mock-tests')
@login_required
def mock_tests():
    tests = MockTest.query.filter_by(
        is_active=True
    ).order_by(MockTest.id.asc()).all()

    test_question_counts = {
        test.id: Question.query.filter_by(
            mock_test_id=test.id,
            question_type='mock_test',
            is_active=True,
        ).count()
        for test in tests
    }

    return render_template(
        'mock_tests.html',
        user=current_user,
        mock_tests=tests,
        test_question_counts=test_question_counts,
    )


# ==========================================
# Create a mock test
# ==========================================

@views.route('/mock-tests/create', methods=['GET', 'POST'])
@admin_required
def create_mock_test():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get(
            'description', ''
        ).strip() or None

        if not title:
            flash(
                'Please enter a name for the mock test.',
                category='error',
            )
            return render_template(
                'create_mock_test.html',
                user=current_user,
            )

        test = MockTest(
            title=title,
            description=description,
            is_active=True,
        )

        db.session.add(test)
        db.session.commit()

        flash(
            'Mock test created successfully. '
            'You can now assign questions to it.',
            category='success',
        )

        return redirect(
            url_for(
                'views.mock_test_detail',
                mock_test_id=test.id,
            )
        )

    return render_template(
        'create_mock_test.html',
        user=current_user,
    )


# ==========================================
# View one mock test and its questions
# ==========================================

@views.route('/mock-test/<int:mock_test_id>')
@login_required
def mock_test_detail(mock_test_id):
    test = db.session.get(MockTest, mock_test_id)

    if test is None:
        abort(404)

    if not test.is_active and not current_user.is_admin:
        abort(404)

    questions = Question.query.filter_by(
        mock_test_id=test.id,
        question_type='mock_test',
    ).order_by(Question.id.asc()).all()

    active_question_count = sum(
        1 for question in questions if question.is_active
    )

    return render_template(
        'mock_test_detail.html',
        user=current_user,
        mock_test=test,
        questions=questions,
        active_question_count=active_question_count,
    )


# ==========================================
# Add a question — mock tests only
# ==========================================

@views.route('/add-question', methods=['GET', 'POST'])
@admin_required
def add_question():
    mock_tests = MockTest.query.order_by(
        MockTest.id.asc()
    ).all()

    selected_mock_test_id = request.values.get(
        'mock_test_id',
        request.args.get('mock_test_id', '')
    ).strip()

    if request.method == 'POST':
        section = request.form.get('section', '').strip()
        domain = request.form.get('domain', '').strip()
        skill = request.form.get('skill', '').strip()
        difficulty = request.form.get('difficulty', '').strip()
        passage = request.form.get('passage', '').strip() or None
        prompt = request.form.get('prompt', '').strip()
        correct_answer = request.form.get(
            'correct_answer', ''
        ).strip()
        explanation = request.form.get(
            'explanation', ''
        ).strip()

        mock_test_id_raw = request.form.get(
            'mock_test_id', ''
        ).strip()

        try:
            mock_test_id = int(mock_test_id_raw)
        except (TypeError, ValueError):
            mock_test_id = None

        selected_test = (
            db.session.get(MockTest, mock_test_id)
            if mock_test_id is not None
            else None
        )

        choices = {
            'A': request.form.get('choice_A', '').strip(),
            'B': request.form.get('choice_B', '').strip(),
            'C': request.form.get('choice_C', '').strip(),
            'D': request.form.get('choice_D', '').strip(),
        }

        valid_mock_test = (
            selected_test is not None and selected_test.is_active
        )

        valid_question = (
            section in ('Reading and Writing', 'Math')
            and bool(domain)
            and bool(skill)
            and difficulty in ('easy', 'medium', 'hard')
            and bool(prompt)
            and all(choices.values())
            and correct_answer in ('A', 'B', 'C', 'D')
            and bool(explanation)
            and valid_mock_test
        )

        if not valid_question:
            flash(
                'Complete all required fields and select an active mock test.',
                category='error',
            )
            return render_template(
                'add_question.html',
                user=current_user,
                mock_tests=mock_tests,
                selected_collection='mock_test',
                selected_mock_test_id=mock_test_id_raw,
            )

        try:
            image_path = save_question_image()
        except ValueError as error:
            flash(str(error), category='error')
            return render_template(
                'add_question.html',
                user=current_user,
                mock_tests=mock_tests,
                selected_collection='mock_test',
                selected_mock_test_id=mock_test_id_raw,
            )

        question = Question(
            question_type='mock_test',
            mock_test_id=mock_test_id,
            image_path=image_path,
            section=section,
            domain=domain,
            skill=skill,
            difficulty=difficulty,
            passage=passage,
            prompt=prompt,
            choices=json.dumps(choices),
            correct_answer=correct_answer,
            explanation=explanation,
            is_active=True,
        )

        try:
            db.session.add(question)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                'Failed to save a mock-test question.'
            )
            flash(
                'The question could not be saved. Please try again.',
                category='error',
            )
            return render_template(
                'add_question.html',
                user=current_user,
                mock_tests=mock_tests,
                selected_collection='mock_test',
                selected_mock_test_id=mock_test_id_raw,
            )

        flash(
            'Question saved to the mock test successfully!',
            category='success',
        )

        return redirect(
            url_for(
                'views.mock_test_detail',
                mock_test_id=mock_test_id,
            )
        )

    return render_template(
        'add_question.html',
        user=current_user,
        mock_tests=mock_tests,
        selected_collection='mock_test',
        selected_mock_test_id=selected_mock_test_id,
    )


# ==========================================
# Legacy Question Bank route
# Existing records are preserved.
# ==========================================

@views.route('/question-bank')
@login_required
def question_bank():
    questions = Question.query.filter(
        Question.question_type == 'question_bank',
        Question.mock_test_id.is_(None),
    ).order_by(Question.id.desc()).all()

    rw_count = Question.query.filter(
        Question.question_type == 'question_bank',
        Question.mock_test_id.is_(None),
        Question.section == 'Reading and Writing',
    ).count()

    math_count = Question.query.filter(
        Question.question_type == 'question_bank',
        Question.mock_test_id.is_(None),
        Question.section == 'Math',
    ).count()

    return render_template(
        'question_bank.html',
        user=current_user,
        questions=questions,
        rw_count=rw_count,
        math_count=math_count,
    )


# ==========================================
# Delete a question
# ==========================================

@views.route(
    '/delete-question/<int:question_id>',
    methods=['POST'],
)
@admin_required
def delete_question(question_id):
    question = db.session.get(Question, question_id)

    if question is None:
        flash('Question not found.', category='error')
        return redirect(url_for('views.mock_tests'))

    mock_test_id = question.mock_test_id
    image_path = question.image_path

    db.session.delete(question)
    db.session.commit()

    if image_path:
        image_file = Path(current_app.static_folder) / image_path

        try:
            image_file.resolve().relative_to(
                Path(current_app.static_folder).resolve()
            )

            if image_file.is_file():
                image_file.unlink()
        except (ValueError, OSError):
            current_app.logger.warning(
                'Could not remove question image: %s',
                image_path,
            )

    flash('Question deleted successfully!', category='success')

    if mock_test_id is not None:
        return redirect(
            url_for(
                'views.mock_test_detail',
                mock_test_id=mock_test_id,
            )
        )

    return redirect(url_for('views.mock_tests'))


# ==========================================
# Legacy Question Bank practice
# ==========================================

@views.route('/start-test', methods=['POST'])
@login_required
def start_test():
    questions = Question.query.filter(
        Question.is_active.is_(True),
        Question.question_type == 'question_bank',
        Question.mock_test_id.is_(None),
    ).order_by(Question.id.asc()).all()

    if not questions:
        flash(
            'The Question Bank has no active questions yet.',
            category='error',
        )
        return redirect(url_for('views.mock_tests'))

    return create_test_attempt(questions, mock_test_id=None)


# ==========================================
# Start one specific mock test
# ==========================================

@views.route(
    '/start-mock-test/<int:mock_test_id>',
    methods=['POST'],
)
@login_required
def start_mock_test(mock_test_id):
    mock_test = db.session.get(MockTest, mock_test_id)

    if mock_test is None or not mock_test.is_active:
        abort(404)

    questions = Question.query.filter_by(
        is_active=True,
        question_type='mock_test',
        mock_test_id=mock_test.id,
    ).order_by(Question.id.asc()).all()

    if not questions:
        flash(
            'This mock test does not have any active questions yet.',
            category='error',
        )
        return redirect(
            url_for(
                'views.mock_test_detail',
                mock_test_id=mock_test.id,
            )
        )

    return create_test_attempt(
        questions,
        mock_test_id=mock_test.id,
    )


# ==========================================
# Shared test-attempt creation
# ==========================================

def create_test_attempt(questions, mock_test_id=None):
    attempt = TestAttempt(
        user_id=current_user.id,
        status='in_progress',
        current_section='reading_writing',
        current_module=1,
        mock_test_id=mock_test_id,
    )

    db.session.add(attempt)
    db.session.flush()

    for question in questions:
        db.session.add(
            TestAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
            )
        )

    db.session.commit()

    return redirect(
        url_for('views.take_test', attempt_id=attempt.id)
    )


# ==========================================
# Take a practice test
# ==========================================

@views.route('/test/<int:attempt_id>', methods=['GET', 'POST'])
@login_required
def take_test(attempt_id):
    attempt = db.session.get(TestAttempt, attempt_id)

    if attempt is None or attempt.user_id != current_user.id:
        abort(404)

    if attempt.status != 'in_progress':
        return redirect(
            url_for('views.test_results', attempt_id=attempt.id)
        )

    answers = TestAnswer.query.filter_by(
        attempt_id=attempt.id
    ).order_by(TestAnswer.id.asc()).all()

    if not answers:
        flash('This test has no questions.', category='error')
        return redirect(url_for('views.mock_tests'))

    current_index = 0

    if request.method == 'POST':
        answer_id = request.form.get('answer_id')
        selected_answer = request.form.get('selected_answer')

        if answer_id:
            try:
                submitted_answer_id = int(answer_id)
            except (TypeError, ValueError):
                submitted_answer_id = None

            answer = (
                db.session.get(TestAnswer, submitted_answer_id)
                if submitted_answer_id is not None
                else None
            )

            if answer and answer.attempt_id == attempt.id:
                if selected_answer in ('A', 'B', 'C', 'D'):
                    answer.selected_answer = selected_answer
                elif selected_answer in ('', None):
                    answer.selected_answer = None

        db.session.commit()

        if request.form.get('action') == 'submit':
            for answer in answers:
                answer.is_correct = (
                    answer.selected_answer in ('A', 'B', 'C', 'D')
                    and answer.selected_answer
                    == answer.question.correct_answer
                )

            attempt.status = 'completed'
            attempt.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            return redirect(
                url_for('views.test_results', attempt_id=attempt.id)
            )

        target_answer_id = (
            request.form.get('next_id')
            or request.form.get('previous_id')
            or request.form.get('target_answer_id')
        )

        if target_answer_id:
            for index, answer in enumerate(answers):
                if str(answer.id) == str(target_answer_id):
                    current_index = index
                    break
            else:
                current_index = 0

        elif request.form.get('action') in ('next', 'previous'):
            try:
                submitted_index = int(
                    request.form.get('current_index', 0)
                )
            except (TypeError, ValueError):
                submitted_index = 0

            submitted_index = max(
                0, min(submitted_index, len(answers) - 1)
            )

            if request.form.get('action') == 'previous':
                current_index = max(0, submitted_index - 1)
            else:
                current_index = min(
                    len(answers) - 1,
                    submitted_index + 1,
                )

    current_answer = answers[current_index]

    return render_template(
        'take_test.html',
        user=current_user,
        attempt=attempt,
        answers=answers,
        current_index=current_index,
        total_questions=len(answers),
        current_answer=current_answer,
    )


# ==========================================
# My Score History
# ==========================================

@views.route('/score-history')
@login_required
def score_history():
    attempts = (
        TestAttempt.query
        .filter_by(
            user_id=current_user.id,
            status='completed'
        )
        .order_by(
            TestAttempt.completed_at.desc(),
            TestAttempt.id.desc()
        )
        .all()
    )

    history = []

    for attempt in attempts:
        answers = TestAnswer.query.filter_by(
            attempt_id=attempt.id
        ).order_by(TestAnswer.id.asc()).all()

        total_questions = len(answers)

        correct_answers = sum(
            1 for answer in answers
            if answer.is_correct is True
        )

        percentage = (
            round(correct_answers / total_questions * 100, 1)
            if total_questions
            else 0
        )

        mock_test = (
            db.session.get(MockTest, attempt.mock_test_id)
            if attempt.mock_test_id
            else None
        )

        history.append({
            'attempt': attempt,
            'mock_test': mock_test,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'percentage': percentage,
        })

    return render_template(
        'score_history.html',
        user=current_user,
        history=history,
    )


# ==========================================
# Test results
# ==========================================

@views.route('/test-results/<int:attempt_id>')
@login_required
def test_results(attempt_id):
    attempt = db.session.get(TestAttempt, attempt_id)

    if attempt is None or attempt.user_id != current_user.id:
        abort(404)

    if attempt.status != 'completed':
        return redirect(
            url_for('views.take_test', attempt_id=attempt.id)
        )

    answers = TestAnswer.query.filter_by(
        attempt_id=attempt.id
    ).order_by(TestAnswer.id.asc()).all()

    total_questions = len(answers)

    correct_answers = sum(
        1 for answer in answers if answer.is_correct is True
    )

    unanswered_questions = sum(
        1 for answer in answers
        if answer.selected_answer not in ('A', 'B', 'C', 'D')
    )

    percentage = (
        round(correct_answers / total_questions * 100, 1)
        if total_questions
        else 0
    )

    return render_template(
        'test_results.html',
        user=current_user,
        attempt=attempt,
        answers=answers,
        total_questions=total_questions,
        correct_answers=correct_answers,
        unanswered_questions=unanswered_questions,
        percentage=percentage,
    )


# ==========================================
# Delete a note belonging to the current user
# ==========================================

@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():
    note_data = request.get_json(silent=True) or {}
    note_id = note_data.get('noteId')

    note = db.session.get(Note, note_id) if note_id else None

    if note and note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()

    return jsonify({})