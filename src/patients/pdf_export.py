# -*- coding: utf-8 -*-
"""
Generation des fiches PDF - Nutri-Wellness Impact

A placer dans : patients/pdf_export.py

Dependance : reportlab  (pip install reportlab)
"""
import os

from django.conf import settings
from django.utils.translation import gettext as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ---------------------------------------------------------
#  CHARTE
# ---------------------------------------------------------
VERT = colors.HexColor("#5a8f3d")
VERT_FONCE = colors.HexColor("#2f5e2f")
VERT_CLAIR = colors.HexColor("#eaf3e3")
ORANGE = colors.HexColor("#f4a020")
ROUGE = colors.HexColor("#d62828")
GRIS = colors.HexColor("#7a8a72")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("NWTitre", parent=s["Title"], textColor=VERT_FONCE,
                         fontSize=16, spaceAfter=4))
    s.add(ParagraphStyle("NWSousTitre", parent=s["Normal"], alignment=TA_CENTER,
                         textColor=GRIS, fontSize=9, spaceAfter=14))
    s.add(ParagraphStyle("NWSection", parent=s["Heading2"], textColor=colors.white,
                         fontSize=10, spaceBefore=12, spaceAfter=6,
                         leftIndent=6, backColor=VERT, borderPadding=5))
    s.add(ParagraphStyle("NWTexte", parent=s["Normal"], fontSize=9, leading=13))
    s.add(ParagraphStyle("NWPetit", parent=s["Normal"], fontSize=7.5, textColor=GRIS))
    return s


def _logo():
    """Retourne le logo s'il est trouve, sinon None."""
    candidats = []
    for base in getattr(settings, "STATICFILES_DIRS", []):
        candidats.append(os.path.join(str(base), "img", "logo.png"))
    if getattr(settings, "STATIC_ROOT", None):
        candidats.append(os.path.join(str(settings.STATIC_ROOT), "img", "logo.png"))
    for chemin in candidats:
        if os.path.exists(chemin):
            try:
                img = Image(chemin, width=2.2 * cm, height=2.2 * cm)
                img.hAlign = "CENTER"
                return img
            except Exception:
                return None
    return None


def _entete(story, st, titre, sous_titre=""):
    logo = _logo()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 4))
    story.append(Paragraph("NUTRI-WELLNESS IMPACT", st["NWSousTitre"]))
    story.append(Paragraph(titre, st["NWTitre"]))
    if sous_titre:
        story.append(Paragraph(sous_titre, st["NWSousTitre"]))
    story.append(Spacer(1, 6))


def _section(story, st, titre):
    story.append(Paragraph(titre, st["NWSection"]))


def _tableau(donnees, colonnes=2):
    """Construit un tableau cle/valeur sur 1 ou 2 colonnes."""
    lignes = [(lbl, "-" if val in (None, "", []) else str(val)) for lbl, val in donnees]
    if colonnes == 2:
        data, tampon = [], []
        for lbl, val in lignes:
            tampon.extend([lbl, val])
            if len(tampon) == 4:
                data.append(tampon)
                tampon = []
        if tampon:
            tampon.extend([""] * (4 - len(tampon)))
            data.append(tampon)
        largeurs = [3.6 * cm, 4.3 * cm, 3.6 * cm, 4.3 * cm]
    else:
        data = [[lbl, val] for lbl, val in lignes]
        largeurs = [5.5 * cm, 10.3 * cm]

    if not data:
        return Spacer(1, 2)

    t = Table(data, colWidths=largeurs)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#eef2ec")),
    ]
    if colonnes == 2:
        style += [("TEXTCOLOR", (0, 0), (0, -1), GRIS), ("TEXTCOLOR", (2, 0), (2, -1), GRIS)]
    else:
        style += [("TEXTCOLOR", (0, 0), (0, -1), GRIS)]
    t.setStyle(TableStyle(style))
    return t


def _oui_non(valeur):
    return _("Yes") if valeur else _("No")


def _pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.2 * cm, "Nutri-Wellness Impact - Food, At The Heart Of Wellbeing")
    canvas.drawRightString(19 * cm, 1.2 * cm, "%s %d" % (_("Page"), doc.page))
    canvas.setStrokeColor(VERT_CLAIR)
    canvas.line(2 * cm, 1.6 * cm, 19 * cm, 1.6 * cm)
    canvas.restoreState()


def _document(buffer, titre_pdf):
    return SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=2.2 * cm,
        title=titre_pdf, author="Nutri-Wellness Impact",
    )


# =========================================================
#  1. BILAN COMPLET DU PATIENT
# =========================================================
def generer_bilan_pdf(buffer, patient, profile):
    st = _styles()
    doc = _document(buffer, _("Dietetic Consultation Form"))
    story = []

    _entete(story, st, _("Dietetic Consultation Form"),
            patient.get_full_name() or patient.email)

    _section(story, st, _("1. Personal Information"))
    story.append(_tableau([
        (_("Full name"), patient.get_full_name() or "-"),
        (_("Email"), patient.email),
        (_("Date of birth"), profile.birth_date),
        (_("Age"), profile.age),
        (_("Gender"), profile.get_gender_display() if profile.gender else ""),
        (_("Phone"), profile.phone),
        (_("Occupation"), profile.occupation),
        (_("Address"), profile.address),
    ]))

    _section(story, st, _("2. Reason for Consultation"))
    story.append(_tableau([
        (_("Main pathology"), profile.get_pathology_display()),
        (_("Reason for consultation"), profile.consultation_reason),
        (_("Comment"), profile.reason_comment),
    ], colonnes=1))

    _section(story, st, _("3. Medical History"))
    story.append(_tableau([
        (_("Diagnosis"), profile.diagnosis),
        (_("Diagnosis date"), profile.diagnosis_date),
        (_("Known diseases"), profile.known_diseases),
        (_("Medical history"), profile.medical_history),
        (_("Family history"), profile.family_history),
        (_("Previous surgeries"), profile.previous_surgeries),
        (_("Medications"), profile.medications),
        (_("Food allergies"), profile.food_allergies),
        (_("Food intolerances"), profile.food_intolerances),
        (_("Family history of CVD"), _oui_non(profile.family_history_cvd)),
    ], colonnes=1))

    _section(story, st, _("4. Lifestyle"))
    story.append(_tableau([
        (_("Sleep (hours per night)"), profile.sleep_hours),
        (_("Sleep quality"), profile.get_sleep_quality_display() if profile.sleep_quality else ""),
        (_("Activity level"), profile.get_activity_level_display() if profile.activity_level else ""),
        (_("Physical activity type"), profile.activity_type),
        (_("Times per week"), profile.activity_frequency),
        (_("Minutes per session"), profile.activity_duration),
        (_("Stress level"), profile.get_stress_level_display() if profile.stress_level else ""),
        (_("Smoking"), _oui_non(profile.smoking)),
        (_("Alcohol"), _oui_non(profile.alcohol)),
        (_("Sweets"), _oui_non(profile.sweets)),
    ]))
    if profile.stress_sources:
        story.append(_tableau([(_("Main stress sources"), profile.stress_sources)], colonnes=1))

    _section(story, st, _("5. Anthropometric Data"))
    imc = "%s (%s)" % (profile.bmi, profile.bmi_status["label"]) if profile.bmi else ""
    story.append(_tableau([
        (_("Height (cm)"), profile.height),
        (_("Current weight (kg)"), profile.weight),
        (_("Usual weight (kg)"), profile.usual_weight),
        (_("Desired weight (kg)"), profile.desired_weight),
        (_("Waist circumference (cm)"), profile.waist_circumference),
        (_("Hip circumference (cm)"), profile.hip_circumference),
        (_("Waist/Hip ratio"), profile.waist_hip_ratio),
        (_("BMI"), imc),
        (_("Left blood pressure"), profile.blood_pressure_left),
        (_("Right blood pressure"), profile.blood_pressure_right),
    ]))

    story.append(PageBreak())
    _entete(story, st, _("Dietetic Consultation Form"),
            "%s (%s)" % (patient.get_full_name() or patient.email, _("continued")))

    _section(story, st, _("6. Eating Habits"))
    story.append(_tableau([
        (_("Number of meals per day"), profile.meals_per_day),
        (_("Snacks included"), _oui_non(profile.has_snacks)),
        (_("Breakfast time"), profile.breakfast_time),
        (_("Lunch time"), profile.lunch_time),
        (_("Dinner time"), profile.dinner_time),
        (_("Snack times"), profile.snack_times),
        (_("Usual place for meals"), profile.get_meal_place_display() if profile.meal_place else ""),
        (_("People you eat with"), profile.get_eat_with_display() if profile.eat_with else ""),
    ]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>%s</b>" % _("Typical Daily Intake"), st["NWTexte"]))
    story.append(_tableau([
        (_("Typical breakfast"), profile.typical_breakfast),
        (_("Typical morning snack"), profile.typical_morning_snack),
        (_("Typical lunch"), profile.typical_lunch),
        (_("Typical afternoon snack"), profile.typical_afternoon_snack),
        (_("Typical dinner"), profile.typical_dinner),
        (_("Typical evening snack"), profile.typical_evening_snack),
    ], colonnes=1))

    story.append(Spacer(1, 6))
    story.append(_tableau([
        (_("Fruits consumption"), profile.get_fruits_consumption_display() if profile.fruits_consumption else ""),
        (_("Vegetables consumption"), profile.get_vegetables_consumption_display() if profile.vegetables_consumption else ""),
        (_("Fatty/sugary foods consumption"), profile.get_fatty_sugary_consumption_display() if profile.fatty_sugary_consumption else ""),
        (_("Glasses of water per day"), profile.water_glasses),
        (_("Litres of water per day"), profile.water_liters),
        (_("Other drinks"), profile.other_drinks),
    ]))

    _section(story, st, _("7. Relationship with Food"))
    story.append(_tableau([
        (_("Appetite"), profile.get_appetite_display() if profile.appetite else ""),
        (_("Snacking"), profile.get_snacking_display() if profile.snacking else ""),
        (_("Snacking moments"), profile.snacking_moments),
        (_("Specific restrictions"), profile.dietary_restrictions),
        (_("Particular behaviors"), profile.eating_behaviors),
    ], colonnes=1))

    _section(story, st, _("8. Goals and Expectations"))
    story.append(_tableau([
        (_("Main expectations"), profile.main_expectations),
        (_("Timeframe to reach goals"), profile.goal_timeframe),
        (_("Motivation level (0-10)"), profile.motivation_level),
    ], colonnes=1))

    _section(story, st, _("9. Practitioner's Notes"))
    story.append(_tableau([
        (_("Practitioner's notes"), profile.practitioner_notes),
        (_("Nutritional diagnosis"), profile.nutritional_diagnosis),
        (_("Risk factors"), profile.risk_factors),
        (_("Proposed dietary plan"), profile.proposed_dietary_plan),
        (_("Specific advice"), profile.specific_advice),
        (_("Date of next appointment"), profile.next_appointment),
    ], colonnes=1))

    story.append(Spacer(1, 22))
    signature = Table([[
        "%s :\n\n\n______________________" % _("Patient's name and signature"),
        "%s :\n\n\n______________________" % _("Nutritionist's signature name"),
    ]], colWidths=[7.9 * cm, 7.9 * cm])
    signature.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), GRIS),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(signature)

    doc.build(story, onFirstPage=_pied, onLaterPages=_pied)
    return buffer


# =========================================================
#  2. FICHE DE SUIVI (consultations)
# =========================================================
def generer_suivi_pdf(buffer, patient, profile, consultations):
    st = _styles()
    doc = _document(buffer, _("Therapeutic Dietetic Follow-up Sheet"))
    story = []

    _entete(story, st, _("Therapeutic Dietetic Follow-up Sheet"),
            patient.get_full_name() or patient.email)

    _section(story, st, _("Patient identification"))
    story.append(_tableau([
        (_("Full name"), patient.get_full_name() or patient.email),
        (_("Age"), profile.age if profile else ""),
        (_("Gender"), profile.get_gender_display() if profile and profile.gender else ""),
        (_("Main pathology"), profile.get_pathology_display() if profile else ""),
        (_("Diagnosis"), profile.diagnosis if profile else ""),
        (_("Height (cm)"), profile.height if profile else ""),
    ]))

    _section(story, st, _("Clinical follow-up"))
    entetes = [_("Date"), _("Weight"), _("BMI"), _("Blood pressure"),
               _("Heart rate"), _("Appetite"), _("Alerts")]
    lignes = [entetes]
    for c in consultations:
        lignes.append([
            c.date_consultation.strftime("%d/%m/%Y") if c.date_consultation else "-",
            "%s kg" % c.weight if c.weight else "-",
            str(c.bmi) if c.bmi else "-",
            c.blood_pressure or "-",
            "%s bpm" % c.heart_rate if c.heart_rate else "-",
            c.get_appetite_display() if c.appetite else "-",
            _("Yes") if c.has_alerts else "-",
        ])

    t = Table(lignes, colWidths=[2.4 * cm, 2.1 * cm, 2.1 * cm, 2.6 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERT_CLAIR]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6e2cf")),
    ]))
    story.append(t)

    # Detail de la derniere consultation
    if consultations:
        derniere = consultations[0]
        _section(story, st, _("Latest consultation - details"))
        story.append(_tableau([
            (_("Salt intake"), derniere.get_salt_intake_display() if derniere.salt_intake else ""),
            (_("Protein intake"), derniere.get_protein_intake_display() if derniere.protein_intake else ""),
            (_("Hydration"), derniere.get_hydration_level_display() if derniere.hydration_level else ""),
            (_("Fruits/Vegetables"), derniere.get_fruits_veg_intake_display() if derniere.fruits_veg_intake else ""),
            (_("Edema"), _oui_non(derniere.edema)),
            (_("Wound healing"), derniere.get_wound_healing_display() if derniere.wound_healing else ""),
        ]))

        story.append(Spacer(1, 4))
        story.append(_tableau([
            (_("Nutritional Diagnosis (PES)"), derniere.nutritional_diagnosis),
            (_("Nutritional goals"), derniere.goals),
            (_("Intervention plan"), derniere.intervention_plan),
            (_("Observations"), derniere.observations),
        ], colonnes=1))

        if derniere.has_alerts:
            _section(story, st, _("Warning Signs"))
            alertes = [
                (_("Rapid weight loss"), derniere.alert_rapid_weight_loss),
                (_("Significant fatigue"), derniere.alert_fatigue),
                (_("Non-healing wound"), derniere.alert_wound),
                (_("Decreased appetite"), derniere.alert_appetite_loss),
                (_("Edema present"), derniere.alert_edema),
            ]
            actifs = [[u"\u2022  " + lbl] for lbl, actif in alertes if actif]
            if actifs:
                ta = Table(actifs, colWidths=[15.8 * cm])
                ta.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (-1, -1), ROUGE),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdecec")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]))
                story.append(ta)

    doc.build(story, onFirstPage=_pied, onLaterPages=_pied)
    return buffer


# =========================================================
#  3. PLAN ALIMENTAIRE
# =========================================================
def generer_plan_pdf(buffer, patient, profile, plans):
    st = _styles()
    doc = _document(buffer, _("Therapeutic Meal Plan"))
    story = []

    sous = patient.get_full_name() or patient.email
    if profile and profile.pathology and profile.pathology != "none":
        sous += " - %s" % profile.get_pathology_display()
    _entete(story, st, _("Therapeutic Meal Plan"), sous)

    entetes = [_("Day"), _("Breakfast"), _("Lunch"), _("Dinner"), _("Snack")]
    lignes = [entetes]
    sp = ParagraphStyle("cell", fontSize=7.5, leading=10)
    for p in plans:
        collations = " / ".join([x for x in [p.morning_snack, p.afternoon_snack, p.evening_snack] if x])
        lignes.append([
            Paragraph("<b>%s</b>" % p.get_day_display(), sp),
            Paragraph(p.breakfast or "-", sp),
            Paragraph(p.lunch or "-", sp),
            Paragraph(p.dinner or "-", sp),
            Paragraph(collations or "-", sp),
        ])

    t = Table(lignes, colWidths=[2.0 * cm, 3.7 * cm, 3.7 * cm, 3.7 * cm, 2.7 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERT_CLAIR]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6e2cf")),
    ]))
    story.append(t)

    if profile and (profile.proposed_dietary_plan or profile.specific_advice):
        _section(story, st, _("Objectives and advice"))
        story.append(_tableau([
            (_("Proposed dietary plan"), profile.proposed_dietary_plan),
            (_("Specific advice"), profile.specific_advice),
            (_("Specific restrictions"), profile.dietary_restrictions),
        ], colonnes=1))

    doc.build(story, onFirstPage=_pied, onLaterPages=_pied)
    return buffer