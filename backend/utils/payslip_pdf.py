# utils/payslip_pdf.py
"""Générateur de PDF pour les fiches de paie"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os


class PayslipPDFGenerator:
    """Générateur de fiches de paie en PDF"""
    
    def __init__(self, payslip, user, company):
        self.payslip = payslip
        self.user = user
        self.company = company
        self.styles = getSampleStyleSheet()
        
        # Styles personnalisés
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        self.section_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1f2937')
        )
    
    def generate(self, output_path):
        """Générer le PDF"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # En-tête
        story.extend(self._build_header())
        story.append(Spacer(1, 1*cm))
        
        # Informations employé
        story.extend(self._build_employee_info())
        story.append(Spacer(1, 0.5*cm))
        
        # Période
        story.extend(self._build_period_info())
        story.append(Spacer(1, 0.5*cm))
        
        # Rémunération
        story.extend(self._build_remuneration_section())
        story.append(Spacer(1, 0.5*cm))
        
        # Déductions
        story.extend(self._build_deductions_section())
        story.append(Spacer(1, 0.5*cm))
        
        # Net à payer
        story.extend(self._build_net_salary())
        story.append(Spacer(1, 0.5*cm))
        
        # Informations complémentaires
        story.extend(self._build_additional_info())
        
        # Pied de page
        story.append(Spacer(1, 1*cm))
        story.extend(self._build_footer())
        
        # Construire le PDF
        doc.build(story)
        
        return output_path
    
    def _build_header(self):
        """Construire l'en-tête"""
        elements = []
        
        # Titre
        title = Paragraph("BULLETIN DE PAIE", self.title_style)
        elements.append(title)
        
        # Informations entreprise
        company_info = f"""
        <b>{self.company.name}</b><br/>
        {self.company.address or ''}<br/>
        {self.company.city or ''} {self.company.postal_code or ''}<br/>
        Matricule Fiscale: {self.company.tax_id or 'N/A'}
        """
        
        company_para = Paragraph(company_info, self.normal_style)
        elements.append(company_para)
        
        return elements
    
    def _build_employee_info(self):
        """Informations de l'employé"""
        elements = []
        
        section_title = Paragraph("INFORMATIONS EMPLOYÉ", self.section_style)
        elements.append(section_title)
        
        data = [
            ['Nom complet:', self.user.get_full_name()],
            ['Matricule:', str(self.user.id)],
            ['Département:', self.user.department.name if self.user.department else 'N/A'],
            ['Fonction:', self.user.get_role_display()]
        ]
        
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_period_info(self):
        """Informations de période"""
        elements = []
        
        month_names = [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        
        period = f"{month_names[self.payslip.month - 1]} {self.payslip.year}"
        
        data = [
            ['Période:', period],
            ['Date d\'édition:', datetime.now().strftime('%d/%m/%Y')]
        ]
        
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_remuneration_section(self):
        """Section rémunération"""
        elements = []
        
        section_title = Paragraph("RÉMUNÉRATION", self.section_style)
        elements.append(section_title)
        
        data = [
            ['Libellé', 'Montant (TND)'],
            ['Salaire de Base', f"{float(self.payslip.base_salary):.3f}"],
            ['Prime Transport', f"{float(self.payslip.transport_allowance):.3f}"],
            ['Prime Panier', f"{float(self.payslip.food_allowance):.3f}"],
            ['Prime Logement', f"{float(self.payslip.housing_allowance):.3f}"],
            ['Prime Responsabilité', f"{float(self.payslip.responsibility_bonus):.3f}"]
        ]
        
        # Ajouter primes variables si présentes
        if float(self.payslip.performance_bonus) > 0:
            data.append(['Prime Performance', f"{float(self.payslip.performance_bonus):.3f}"])
        
        if float(self.payslip.overtime_pay) > 0:
            data.append(['Heures Supplémentaires', f"{float(self.payslip.overtime_pay):.3f}"])
        
        # Total brut
        data.append(['SALAIRE BRUT', f"{float(self.payslip.gross_salary):.3f}"])
        
        table = Table(data, colWidths=[12*cm, 5*cm])
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            
            # Corps
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            
            # Ligne total
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            
            # Alignement
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            
            # Espacement
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            
            # Grille
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_deductions_section(self):
        """Section déductions"""
        elements = []
        
        section_title = Paragraph("DÉDUCTIONS", self.section_style)
        elements.append(section_title)
        
        data = [
            ['Libellé', 'Montant (TND)']
        ]
        
        # Ajouter les déductions non nulles
        if float(self.payslip.leave_deduction) > 0:
            data.append(['Congés non payés', f"-{float(self.payslip.leave_deduction):.3f}"])
        
        if float(self.payslip.absence_deduction) > 0:
            data.append(['Absences', f"-{float(self.payslip.absence_deduction):.3f}"])
        
        if float(self.payslip.advance_deduction) > 0:
            data.append(['Avances sur salaire', f"-{float(self.payslip.advance_deduction):.3f}"])
        
        if float(self.payslip.late_deduction) > 0:
            data.append(['Retards', f"-{float(self.payslip.late_deduction):.3f}"])
        
        # Cotisations sociales
        data.append(['CNSS (9.18%)', f"-{float(self.payslip.cnss_employee):.3f}"])
        data.append(['IRPP', f"-{float(self.payslip.irpp):.3f}"])
        
        # Total déductions
        data.append(['TOTAL DÉDUCTIONS', f"-{float(self.payslip.total_deductions):.3f}"])
        
        table = Table(data, colWidths=[12*cm, 5*cm])
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            
            # Corps
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            
            # Ligne total
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fee2e2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            
            # Alignement
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            
            # Espacement
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            
            # Grille
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_net_salary(self):
        """Salaire net à payer"""
        elements = []
        
        data = [
            ['SALAIRE NET À PAYER', f"{float(self.payslip.net_salary):.3f} TND"]
        ]
        
        table = Table(data, colWidths=[12*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_additional_info(self):
        """Informations complémentaires"""
        elements = []
        
        section_title = Paragraph("INFORMATIONS COMPLÉMENTAIRES", self.section_style)
        elements.append(section_title)
        
        data = [
            ['Jours ouvrables:', str(self.payslip.working_days)],
            ['Jours travaillés:', str(self.payslip.days_worked)],
            ['Jours de congés:', str(self.payslip.leave_days)],
            ['Jours d\'absence:', str(self.payslip.absence_days)]
        ]
        
        table = Table(data, colWidths=[8.5*cm, 8.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_footer(self):
        """Pied de page"""
        elements = []
        
        footer_text = f"""
        <i>Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i><br/>
        <i>Ce bulletin de paie est conforme à la législation tunisienne en vigueur.</i>
        """
        
        footer_para = Paragraph(footer_text, self.normal_style)
        elements.append(footer_para)
        
        return elements


def generate_payslip_pdf(payslip, user, company, output_dir='payslips'):
    """
    Générer un PDF de fiche de paie
    
    Args:
        payslip: Instance de Payslip
        user: Instance de User
        company: Instance de Company
        output_dir: Répertoire de sortie
        
    Returns:
        str: Chemin du fichier généré
    """
    # Créer le répertoire si nécessaire
    os.makedirs(output_dir, exist_ok=True)
    
    # Nom du fichier
    filename = f"fiche_paie_{user.username}_{payslip.year}_{payslip.month:02d}.pdf"
    output_path = os.path.join(output_dir, filename)
    
    # Générer le PDF
    generator = PayslipPDFGenerator(payslip, user, company)
    generator.generate(output_path)
    
    return output_path