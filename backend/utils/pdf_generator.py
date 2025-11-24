# utils/pdf_generator.py
"""
Générateur de PDF professionnel pour factures et documents comptables
Design moderne avec mise en page responsive et branding personnalisable
"""
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
import io
import os
from datetime import datetime
from decimal import Decimal
import qrcode
from PIL import Image as PILImage

class AdvancedPDFGenerator:
    """Générateur de PDF avancé avec design moderne"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.register_custom_fonts()
        self.setup_custom_styles()
    
    def register_custom_fonts(self):
        """Enregistrer les polices personnalisées"""
        try:
            # Essayer d'enregistrer des polices professionnelles
            font_paths = {
                'Montserrat': {
                    'normal': 'static/fonts/Montserrat-Regular.ttf',
                    'bold': 'static/fonts/Montserrat-Bold.ttf',
                    'italic': 'static/fonts/Montserrat-Italic.ttf',
                },
                'OpenSans': {
                    'normal': 'static/fonts/OpenSans-Regular.ttf',
                    'bold': 'static/fonts/OpenSans-Bold.ttf',
                }
            }
            
            for font_name, fonts in font_paths.items():
                for style, path in fonts.items():
                    if os.path.exists(path):
                        pdfmetrics.registerFont(TTFont(f"{font_name}-{style}", path))
            
        except:
            # Utiliser les polices par défaut si personnalisées non disponibles
            print("Polices personnalisées non trouvées, utilisation des polices par défaut")
    
    def setup_custom_styles(self):
        """Configurer les styles personnalisés"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=TA_LEFT,
            spaceAfter=12
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Style pour le corps de texte
        self.styles.add(ParagraphStyle(
            name='BodyText',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#4B5563'),
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Style pour les montants
        self.styles.add(ParagraphStyle(
            name='Amount',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#059669'),
            alignment=TA_RIGHT
        ))
        
        # Style pour les en-têtes de tableau
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.white,
            alignment=TA_CENTER,
            backColor=colors.HexColor('#3B82F6')
        ))
        
        # Style pour le pied de page
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica-Oblique',
            fontSize=8,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER
        ))

    def create_invoice_pdf(self, invoice, company, customer, template_config=None):
        """
        Créer une facture PDF professionnelle avec design moderne
        """
        buffer = io.BytesIO()
        
        # Configuration du document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Contenu du document
        story = []
        
        # En-tête avec design moderne
        story.extend(self._create_header(company, invoice, template_config))
        
        # Informations client et facture
        story.extend(self._create_invoice_info(invoice, customer))
        
        # Tableau des articles
        story.extend(self._create_items_table(invoice))
        
        # Totaux et notes
        story.extend(self._create_totals_section(invoice))
        
        # Pied de page
        story.extend(self._create_footer(company))
        
        # QR Code pour paiement rapide
        story.extend(self._create_qr_code_section(invoice, company))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()

    def _create_header(self, company, invoice, template_config):
        """Créer l'en-tête de la facture"""
        elements = []
        
        # Bandeau coloré en haut
        header_table = Table([
            ['', f'FACTURE N° {invoice.invoice_number}', ''],
        ], colWidths=['30%', '40%', '30%'])
        
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
            ('FONT', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 16),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#3B82F6')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#3B82F6')),
            ('ROWBACKGROUNDS', (0, 0), (-1, 0), [colors.white, colors.HexColor('#3B82F6'), colors.white]),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 20))
        
        # Informations de l'entreprise
        company_info = [
            [self._create_company_logo(company), self._create_company_details(company)],
        ]
        
        company_table = Table(company_info, colWidths=['30%', '70%'])
        company_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(company_table)
        elements.append(Spacer(1, 15))
        
        return elements

    def _create_company_logo(self, company):
        """Créer la section logo de l'entreprise"""
        logo_content = []
        
        # Placeholder pour le logo - en production, utiliser le vrai logo
        if hasattr(company, 'logo_path') and company.logo_path:
            try:
                logo = Image(company.logo_path, width=2*inch, height=1*inch)
                logo_content.append(logo)
            except:
                # Fallback si logo non disponible
                logo_content.append(Paragraph(
                    f"<b>{company.name}</b>",
                    self.styles['MainTitle']
                ))
        else:
            # Design élégant sans logo
            logo_content.append(Paragraph(
                f"<b>{company.name}</b>",
                self.styles['MainTitle']
            ))
            
            if company.legal_name and company.legal_name != company.name:
                logo_content.append(Paragraph(
                    company.legal_name,
                    self.styles['BodyText']
                ))
        
        return logo_content

    def _create_company_details(self, company):
        """Créer les détails de l'entreprise"""
        details = []
        
        # Adresse
        address_lines = []
        if company.address:
            address_lines.append(company.address)
        if company.city or company.postal_code:
            city_line = f"{company.postal_code or ''} {company.city or ''}".strip()
            if city_line:
                address_lines.append(city_line)
        if company.country and company.country != 'Tunisie':
            address_lines.append(company.country)
        
        for line in address_lines:
            details.append(Paragraph(line, self.styles['BodyText']))
        
        # Contacts
        if company.phone:
            details.append(Paragraph(f"Tél: {company.phone}", self.styles['BodyText']))
        if company.email:
            details.append(Paragraph(f"Email: {company.email}", self.styles['BodyText']))
        if company.website:
            details.append(Paragraph(f"Web: {company.website}", self.styles['BodyText']))
        
        # Informations fiscales
        if company.tax_id:
            details.append(Spacer(1, 6))
            details.append(Paragraph(
                f"<b>Matricule Fiscale:</b> {company.tax_id}",
                self.styles['BodyText']
            ))
        
        return details

    def _create_invoice_info(self, invoice, customer):
        """Créer la section informations facture et client"""
        elements = []
        
        # Tableau à deux colonnes: Client vs Informations Facture
        info_data = [
            [
                # Colonne Client
                [
                    Paragraph("<b>FACTURÉ À</b>", self.styles['SubTitle']),
                    Paragraph(customer.name, self.styles['BodyText']),
                    *self._format_customer_address(customer),
                    *self._format_customer_contacts(customer),
                    *self._format_customer_tax_info(customer)
                ],
                # Colonne Informations Facture
                [
                    Paragraph("<b>DÉTAILS DE LA FACTURE</b>", self.styles['SubTitle']),
                    self._create_info_row("N° Facture", invoice.invoice_number),
                    self._create_info_row("Date d'émission", invoice.issue_date.strftime('%d/%m/%Y')),
                    self._create_info_row("Date d'échéance", invoice.due_date.strftime('%d/%m/%Y')),
                    self._create_info_row("Devise", invoice.currency),
                    self._create_info_row("Conditions", f"{invoice.payment_terms} jours" if invoice.payment_terms else "À réception")
                ]
            ]
        ]
        
        info_table = Table(info_data, colWidths=['50%', '50%'])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F3F4F6')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F3F4F6')),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements

    def _format_customer_address(self, customer):
        """Formatter l'adresse du client"""
        address_elements = []
        if customer.address:
            address_elements.append(Paragraph(customer.address, self.styles['BodyText']))
        
        city_line = f"{customer.postal_code or ''} {customer.city or ''}".strip()
        if city_line:
            address_elements.append(Paragraph(city_line, self.styles['BodyText']))
        
        if customer.country and customer.country != 'Tunisie':
            address_elements.append(Paragraph(customer.country, self.styles['BodyText']))
        
        return address_elements

    def _format_customer_contacts(self, customer):
        """Formatter les contacts du client"""
        contacts = []
        if customer.email:
            contacts.append(Paragraph(f"Email: {customer.email}", self.styles['BodyText']))
        if customer.phone:
            contacts.append(Paragraph(f"Tél: {customer.phone}", self.styles['BodyText']))
        return contacts

    def _format_customer_tax_info(self, customer):
        """Formatter les informations fiscales du client"""
        tax_info = []
        if customer.tax_id:
            tax_info.append(Spacer(1, 6))
            tax_info.append(Paragraph(
                f"<b>Matricule Fiscale:</b> {customer.tax_id}",
                self.styles['BodyText']
            ))
        return tax_info

    def _create_info_row(self, label, value):
        """Créer une ligne d'information formatée"""
        return Table([
            [Paragraph(f"<b>{label}:</b>", self.styles['BodyText']), Paragraph(value, self.styles['BodyText'])]
        ], colWidths=['40%', '60%'])

    def _create_items_table(self, invoice):
        """Créer le tableau des articles de la facture"""
        elements = []
        
        # En-tête du tableau
        elements.append(Paragraph("<b>DÉTAIL DES ARTICLES</b>", self.styles['SubTitle']))
        elements.append(Spacer(1, 10))
        
        # Données du tableau
        table_data = [['Description', 'Qté', 'Prix U.', 'TVA %', 'Montant']]
        
        for item in invoice.items:
            tax_rate = item.tax_rate.rate if item.tax_rate else 0
            table_data.append([
                Paragraph(item.description, self.styles['BodyText']),
                str(item.quantity),
                f"{item.unit_price:.2f} {invoice.currency}",
                f"{tax_rate}%" if tax_rate > 0 else "Exo",
                f"{item.amount:.2f} {invoice.currency}"
            ])
        
        # Créer le tableau
        item_table = Table(table_data, colWidths=['50%', '10%', '15%', '10%', '15%'])
        
        # Style du tableau
        item_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1E40AF')),
            
            # Alternance des couleurs de ligne
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(item_table)
        elements.append(Spacer(1, 15))
        
        return elements

    def _create_totals_section(self, invoice):
        """Créer la section des totaux"""
        elements = []
        
        # Tableau des totaux aligné à droite
        totals_data = [
            ['Sous-total:', f"{invoice.subtotal:.2f} {invoice.currency}"],
            ['Montant TVA:', f"{invoice.tax_amount:.2f} {invoice.currency}"],
            ['', ''],
            ['<b>TOTAL FACTURE:</b>', f"<b>{invoice.total_amount:.2f} {invoice.currency}</b>"],
            ['Montant payé:', f"{invoice.amount_paid:.2f} {invoice.currency}"],
            ['<b>SOLDE DÛ:</b>', f"<b>{invoice.balance_due:.2f} {invoice.currency}</b>"]
        ]
        
        totals_table = Table(totals_data, colWidths=['60%', '40%'])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, 3), (-1, 3), 12),
            ('FONTSIZE', (0, 5), (-1, 5), 12),
            ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 5), (-1, 5), colors.HexColor('#DC2626') if invoice.balance_due > 0 else colors.HexColor('#059669')),
            ('LINEABOVE', (0, 3), (-1, 3), 1, colors.HexColor('#3B82F6')),
            ('LINEABOVE', (0, 5), (-1, 5), 1, colors.HexColor('#DC2626') if invoice.balance_due > 0 else colors.HexColor('#059669')),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 10),
        ]))
        
        # Conteneur avec fond coloré
        container_data = [[totals_table]]
        container_table = Table(container_data, colWidths=['60%'])
        container_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 15),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]))
        
        elements.append(container_table)
        elements.append(Spacer(1, 20))
        
        # Notes et conditions
        if invoice.notes or invoice.terms_conditions:
            elements.append(self._create_notes_section(invoice))
        
        return elements

    def _create_notes_section(self, invoice):
        """Créer la section notes et conditions"""
        elements = []
        
        notes_content = []
        if invoice.notes:
            notes_content.append(Paragraph("<b>Notes:</b>", self.styles['SubTitle']))
            notes_content.append(Paragraph(invoice.notes, self.styles['BodyText']))
            notes_content.append(Spacer(1, 10))
        
        if invoice.terms_conditions:
            notes_content.append(Paragraph("<b>Conditions de paiement:</b>", self.styles['SubTitle']))
            notes_content.append(Paragraph(invoice.terms_conditions, self.styles['BodyText']))
        
        if notes_content:
            notes_table = Table([[notes_content]], colWidths=['100%'])
            notes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF3C7')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F59E0B')),
                ('PADDING', (0, 0), (-1, -1), 12),
            ]))
            
            elements.append(notes_table)
            elements.append(Spacer(1, 15))
        
        return elements

    def _create_qr_code_section(self, invoice, company):
        """Créer la section QR Code pour paiement rapide"""
        elements = []
        
        try:
            # Générer le QR code avec les informations de paiement
            payment_info = f"""
            Paiement Facture {invoice.invoice_number}
            Entreprise: {company.name}
            Montant: {invoice.balance_due:.2f} {invoice.currency}
            Date d'échéance: {invoice.due_date.strftime('%d/%m/%Y')}
            Référence: {invoice.invoice_number}
            """
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=2,
            )
            qr.add_data(payment_info)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Ajouter le QR code au PDF
            qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
            
            qr_table = Table([
                [qr_image, 
                 Paragraph(
                     f"<b>Scannez pour payer</b><br/>"
                     f"Facture: {invoice.invoice_number}<br/>"
                     f"Montant: {invoice.balance_due:.2f} {invoice.currency}<br/>"
                     f"Échéance: {invoice.due_date.strftime('%d/%m/%Y')}",
                     self.styles['BodyText']
                 )]
            ], colWidths=['30%', '70%'])
            
            qr_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDF4')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BBF7D0')),
            ]))
            
            elements.append(qr_table)
            elements.append(Spacer(1, 15))
            
        except Exception as e:
            print(f"Erreur génération QR code: {e}")
            # Continuer sans QR code en cas d'erreur
        
        return elements

    def _create_footer(self, company):
        """Créer le pied de page"""
        elements = []
        
        footer_text = [
            f"{company.name} - {company.legal_name or ''}",
            f"{company.address or ''} - {company.postal_code or ''} {company.city or ''}",
            f"Tél: {company.phone or 'N/A'} - Email: {company.email or 'N/A'}",
            f"Matricule Fiscale: {company.tax_id or 'N/A'}",
            f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            "FlowERP - Système de gestion intégré"
        ]
        
        for line in footer_text:
            if line.strip():
                elements.append(Paragraph(line, self.styles['Footer']))
        
        return elements

    def create_financial_report(self, report_data, company, report_type="profit_loss"):
        """
        Créer un rapport financier PDF avancé
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # En-tête du rapport
        story.extend(self._create_report_header(company, report_type, report_data))
        
        # Métriques principales
        story.extend(self._create_financial_metrics(report_data))
        
        # Graphiques (si données disponibles)
        story.extend(self._create_financial_charts(report_data))
        
        # Tableaux détaillés
        story.extend(self._create_detailed_tables(report_data))
        
        # Analyse et commentaires
        story.extend(self._create_analysis_section(report_data))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_report_header(self, company, report_type, report_data):
        """Créer l'en-tête du rapport financier"""
        elements = []
        
        report_titles = {
            "profit_loss": "RAPPORT PROFIT & LOSS",
            "cashflow": "RAPPORT TRÉSORERIE",
            "balance": "BILAN COMPTABLE"
        }
        
        title = report_titles.get(report_type, "RAPPORT FINANCIER")
        
        elements.append(Paragraph(title, self.styles['MainTitle']))
        elements.append(Paragraph(
            f"Période: {report_data.get('period_start', 'N/A')} à {report_data.get('period_end', 'N/A')}",
            self.styles['SubTitle']
        ))
        elements.append(Paragraph(company.name, self.styles['BodyText']))
        elements.append(Spacer(1, 20))
        
        return elements

    def _create_financial_metrics(self, report_data):
        """Créer les métriques financières principales"""
        elements = []
        
        metrics = report_data.get('key_metrics', {})
        if metrics:
            metrics_data = [
                ['Chiffre d\'affaires', f"{metrics.get('revenue', 0):.2f} TND"],
                ['Marge brute', f"{metrics.get('gross_margin', 0):.2f} TND"],
                ['Marge nette', f"{metrics.get('net_margin', 0):.2f} TND"],
                ['Trésorerie', f"{metrics.get('cash_balance', 0):.2f} TND"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=['70%', '30%'])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ]))
            
            elements.append(metrics_table)
            elements.append(Spacer(1, 15))
        
        return elements

# Alias pour la compatibilité
PDFGenerator = AdvancedPDFGenerator