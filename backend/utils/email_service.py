# utils/email_service.py
"""
Service d'email avancé pour la facturation et la communication client
Templates HTML modernes, suivi des ouvertures, et gestion des pièces jointes
"""
import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Dict, Optional
import jinja2
from urllib.parse import quote
import base64

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedEmailService:
    """Service d'email avancé avec templates HTML et suivi"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'FlowERP Facturation')
        
        # Initialisation du moteur de templates
        self.template_loader = jinja2.FileSystemLoader(searchpath='templates/emails')
        self.template_env = jinja2.Environment(loader=self.template_loader)
        
        # Configuration
        self.tracking_enabled = os.getenv('EMAIL_TRACKING', 'True').lower() == 'true'
        
    def send_invoice_email(self, invoice, customer, pdf_data=None, language='fr'):
        """
        Envoyer une facture par email avec template professionnel
        """
        try:
            # Préparer les données du template
            template_data = {
                'invoice': invoice,
                'customer': customer,
                'company': invoice.company,
                'current_date': datetime.now().strftime('%d/%m/%Y'),
                'due_date': invoice.due_date.strftime('%d/%m/%Y'),
                'total_amount': f"{invoice.total_amount:,.2f}".replace(',', ' ').replace('.', ','),
                'balance_due': f"{invoice.balance_due:,.2f}".replace(',', ' ').replace('.', ','),
                'tracking_pixel': self._generate_tracking_pixel('invoice', invoice.id, customer.id) if self.tracking_enabled else ''
            }
            
            # Générer le contenu HTML
            html_content = self._render_template('invoice_email.html', template_data, language)
            text_content = self._generate_text_version(template_data)
            
            # Sujet de l'email
            subject = f"Facture {invoice.invoice_number} - {invoice.company.name}"
            
            # Pièces jointes
            attachments = []
            if pdf_data:
                attachments.append({
                    'filename': f"Facture_{invoice.invoice_number}.pdf",
                    'data': pdf_data,
                    'mimetype': 'application/pdf'
                })
            
            # Envoyer l'email
            return self._send_email(
                to_email=customer.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                attachments=attachments,
                category='invoice'
            )
            
        except Exception as e:
            logger.error(f"Erreur envoi email facture: {e}")
            return False
    
    def send_payment_reminder(self, invoice, customer, reminder_stage=1, language='fr'):
        """
        Envoyer une relance de paiement
        """
        try:
            # Déterminer le template selon le stade de relance
            if reminder_stage == 1:
                template_name = 'reminder_stage1.html'
                subject = f"Rappel de paiement - Facture {invoice.invoice_number}"
            elif reminder_stage == 2:
                template_name = 'reminder_stage2.html'
                subject = f"Deuxième rappel - Facture {invoice.invoice_number}"
            else:
                template_name = 'reminder_stage3.html'
                subject = f"Dernier rappel - Facture {invoice.invoice_number} - Mise en demeure"
            
            days_overdue = (datetime.now().date() - invoice.due_date).days
            
            template_data = {
                'invoice': invoice,
                'customer': customer,
                'company': invoice.company,
                'reminder_stage': reminder_stage,
                'days_overdue': days_overdue,
                'current_date': datetime.now().strftime('%d/%m/%Y'),
                'due_date': invoice.due_date.strftime('%d/%m/%Y'),
                'total_amount': f"{invoice.total_amount:,.2f}".replace(',', ' ').replace('.', ','),
                'balance_due': f"{invoice.balance_due:,.2f}".replace(',', ' ').replace('.', ','),
                'tracking_pixel': self._generate_tracking_pixel(f'reminder_{reminder_stage}', invoice.id, customer.id) if self.tracking_enabled else ''
            }
            
            html_content = self._render_template(template_name, template_data, language)
            text_content = self._generate_reminder_text_version(template_data)
            
            return self._send_email(
                to_email=customer.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                category='reminder'
            )
            
        except Exception as e:
            logger.error(f"Erreur envoi relance: {e}")
            return False
    
    def send_payment_confirmation(self, payment, invoice, customer, language='fr'):
        """
        Envoyer une confirmation de paiement
        """
        try:
            template_data = {
                'payment': payment,
                'invoice': invoice,
                'customer': customer,
                'company': invoice.company,
                'payment_date': payment.payment_date.strftime('%d/%m/%Y'),
                'amount': f"{payment.amount:,.2f}".replace(',', ' ').replace('.', ','),
                'current_date': datetime.now().strftime('%d/%m/%Y'),
                'tracking_pixel': self._generate_tracking_pixel('payment_confirmation', payment.id, customer.id) if self.tracking_enabled else ''
            }
            
            html_content = self._render_template('payment_confirmation.html', template_data, language)
            text_content = self._generate_payment_text_version(template_data)
            
            subject = f"Confirmation de paiement - Facture {invoice.invoice_number}"
            
            return self._send_email(
                to_email=customer.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                category='payment_confirmation'
            )
            
        except Exception as e:
            logger.error(f"Erreur envoi confirmation paiement: {e}")
            return False
    
    def send_financial_alert(self, to_emails, alert_type, data, language='fr'):
        """
        Envoyer une alerte financière
        """
        try:
            template_data = {
                'alert_type': alert_type,
                'data': data,
                'current_date': datetime.now().strftime('%d/%m/%Y'),
                'current_time': datetime.now().strftime('%H:%M'),
                'tracking_pixel': self._generate_tracking_pixel(f'alert_{alert_type}', 0, 0) if self.tracking_enabled else ''
            }
            
            html_content = self._render_template('financial_alert.html', template_data, language)
            text_content = self._generate_alert_text_version(template_data)
            
            subjects = {
                'overdue_invoices': f"🚨 Alertes - {data.get('count', 0)} factures en retard",
                'cashflow_low': "⚠️ Alerte Trésorerie - Niveau bas",
                'high_risk_customer': "🔍 Alerte - Client à risque élevé",
                'monthly_report': f"📊 Rapport Financier {datetime.now().strftime('%B %Y')}"
            }
            
            subject = subjects.get(alert_type, "Alerte Financière")
            
            # Envoyer à plusieurs destinataires
            results = []
            for email in to_emails:
                result = self._send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    category=f'alert_{alert_type}'
                )
                results.append(result)
            
            return all(results)
            
        except Exception as e:
            logger.error(f"Erreur envoi alerte financière: {e}")
            return False
    
    def _render_template(self, template_name, data, language='fr'):
        """Rendre un template HTML avec les données"""
        try:
            # Essayer la version localisée d'abord
            localized_template = f"{language}/{template_name}"
            template = self.template_env.get_template(localized_template)
        except jinja2.TemplateNotFound:
            try:
                # Fallback sur la version par défaut
                template = self.template_env.get_template(template_name)
            except jinja2.TemplateNotFound:
                # Template de secours
                return self._get_fallback_template(data)
        
        return template.render(**data)
    
    def _send_email(self, to_email, subject, html_content, text_content, 
                   attachments=None, category='general'):
        """Envoyer un email avec gestion d'erreurs complète"""
        try:
            # Vérification des paramètres SMTP
            if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
                logger.error("Configuration SMTP manquante")
                return False
            
            # Création du message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Headers pour le tracking et la catégorisation
            msg['X-Mailer'] = 'FlowERP Billing System'
            msg['X-Category'] = category
            msg['X-Priority'] = '3'  # Normal priority
            
            # Corps du message
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Pièces jointes
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(
                        attachment['data'],
                        Name=attachment['filename']
                    )
                    part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                    msg.attach(part)
            
            # Connexion et envoi
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email envoyé avec succès à {to_email} - Catégorie: {category}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Erreur d'authentification SMTP")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Erreur SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi: {e}")
            return False
    
    def _generate_tracking_pixel(self, email_type, entity_id, customer_id):
        """Générer un pixel de tracking pour les statistiques"""
        if not self.tracking_enabled:
            return ""
        
        tracking_url = f"https://your-domain.com/track?type={email_type}&entity={entity_id}&customer={customer_id}&t={int(datetime.now().timestamp())}"
        
        return f'''
        <img src="{tracking_url}" width="1" height="1" style="display:none;" 
             alt="Tracking pixel" onload="this.parentNode.removeChild(this);" />
        '''
    
    def _generate_text_version(self, data):
        """Générer la version texte de l'email de facture"""
        invoice = data['invoice']
        customer = data['customer']
        company = data['company']
        
        return f"""
FACTURE {invoice.invoice_number}

Bonjour {customer.name},

Veuillez trouver ci-joint la facture {invoice.invoice_number} d'un montant de {data['total_amount']} {invoice.currency}.

DÉTAILS DE LA FACTURE:
- Numéro: {invoice.invoice_number}
- Date d'émission: {data['current_date']}
- Date d'échéance: {data['due_date']}
- Montant total: {data['total_amount']} {invoice.currency}
- Solde dû: {data['balance_due']} {invoice.currency}

INFORMATIONS DE PAIEMENT:
Vous pouvez régler cette facture par virement bancaire ou chèque.

Coordonnées bancaires:
- Banque: [Votre Banque]
- IBAN: [Votre IBAN]
- BIC/SWIFT: [Votre BIC]
- Référence: {invoice.invoice_number}

Pour toute question concernant cette facture, veuillez contacter:
{company.name}
Tél: {company.phone or 'Non renseigné'}
Email: {company.email or 'Non renseigné'}

Cordialement,
L'équipe {company.name}
"""
    
    def _generate_reminder_text_version(self, data):
        """Générer la version texte des relances"""
        invoice = data['invoice']
        customer = data['customer']
        company = data['company']
        
        base_text = f"""
RAPPEL DE PAIEMENT - FACTURE {invoice.invoice_number}

Bonjour {customer.name},
"""
        
        if data['reminder_stage'] == 1:
            base_text += f"""
Nous souhaitons vous rappeler que la facture {invoice.invoice_number} d'un montant de {data['total_amount']} {invoice.currency} était due le {data['due_date']}.

À ce jour, un solde de {data['balance_due']} {invoice.currency} reste à régler.

Nous vous remercions de bien vouloir procéder au paiement dans les plus brefs délais.
"""
        elif data['reminder_stage'] == 2:
            base_text += f"""
DEUXIÈME RAPPEL - FACTURE {invoice.invoice_number}

Notre premier rappel concernant la facture {invoice.invoice_number} d'un montant de {data['total_amount']} {invoice.currency} échue le {data['due_date']} est resté sans réponse.

Le solde impayé s'élève à {data['balance_due']} {invoice.currency} et est en retard de {data['days_overdue']} jours.

Nous vous prions de régulariser cette situation dans les 48 heures.
"""
        else:
            base_text += f"""
DERNIER RAPPEL - FACTURE {invoice.invoice_number}

Malgré nos précédents rappels, la facture {invoice.invoice_number} d'un montant de {data['total_amount']} {invoice.currency} échue le {data['due_date']} n'est toujours pas réglée.

Le solde impayé de {data['balance_due']} {invoice.currency} est en retard de {data['days_overdue']} jours.

À défaut de régularisation sous 24 heures, nous serons dans l'obligation de transmettre ce dossier à notre service contentieux.

Nous vous prions de croire, Madame, Monsieur, à l'expression de nos salutations distinguées.
"""
        
        base_text += f"""

INFORMATIONS DE PAIEMENT:
Coordonnées bancaires:
- IBAN: [Votre IBAN]
- BIC: [Votre BIC]
- Référence: {invoice.invoice_number}

Pour toute question, contactez-nous:
{company.name}
{company.phone or ''}
{company.email or ''}
"""
        
        return base_text
    
    def _generate_payment_text_version(self, data):
        """Générer la version texte des confirmations de paiement"""
        payment = data['payment']
        invoice = data['invoice']
        customer = data['customer']
        company = data['company']
        
        return f"""
CONFIRMATION DE PAIEMENT

Bonjour {customer.name},

Nous accusons réception de votre paiement concernant la facture {invoice.invoice_number}.

DÉTAILS DU PAIEMENT:
- Facture: {invoice.invoice_number}
- Montant payé: {data['amount']} {payment.currency}
- Date de paiement: {data['payment_date']}
- Méthode: {payment.payment_method}
- Référence: {payment.payment_reference or 'Non renseignée'}

Votre règlement a été enregistré avec succès. Nous vous remercions pour votre promptitude.

Pour toute question, n'hésitez pas à nous contacter.

Cordialement,
L'équipe {company.name}

{company.phone or ''}
{company.email or ''}
"""
    
    def _generate_alert_text_version(self, data):
        """Générer la version texte des alertes"""
        alert_type = data['alert_type']
        
        if alert_type == 'overdue_invoices':
            count = data['data'].get('count', 0)
            total_amount = data['data'].get('total_amount', 0)
            
            return f"""
ALERTE FACTURES EN RETARD

{count} facture(s) sont en retard de paiement pour un montant total de {total_amount:,.2f} TND.

Détail des factures en retard:
{self._format_overdue_invoices(data['data'].get('invoices', []))}

Veuillez prendre les mesures nécessaires pour le recouvrement.
"""
        
        elif alert_type == 'cashflow_low':
            current_balance = data['data'].get('current_balance', 0)
            min_threshold = data['data'].get('min_threshold', 0)
            
            return f"""
ALERTE TRÉSORERIE BASSE

La trésorerie actuelle est de {current_balance:,.2f} TND, en dessous du seuil minimum de {min_threshold:,.2f} TND.

Actions recommandées:
- Relancer les clients en retard
- Reporter les dépenses non essentielles
- Vérifier les encaissements à venir
"""
        
        else:
            return f"""
ALERTE FINANCIÈRE - {alert_type.upper()}

Une alerte financière a été déclenchée le {data['current_date']} à {data['current_time']}.

Type: {alert_type}
Données: {data['data']}

Veuillez consulter le tableau de bord pour plus de détails.
"""
    
    def _format_overdue_invoices(self, invoices):
        """Formatter la liste des factures en retard"""
        if not invoices:
            return "Aucune facture en retard."
        
        formatted = ""
        for inv in invoices:
            days_overdue = (datetime.now().date() - inv.due_date).days
            formatted += f"- {inv.invoice_number}: {inv.balance_due:,.2f} TND ({days_overdue} jours de retard)\n"
        
        return formatted
    
    def _get_fallback_template(self, data):
        """Template de secours si les templates sont manquants"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #3B82F6; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
        .amount {{ font-size: 18px; font-weight: bold; color: #059669; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FlowERP Facturation</h1>
    </div>
    
    <div class="content">
        <h2>Communication importante</h2>
        <p>Bonjour,</p>
        
        <p>Vous recevez cet email car un document important vous concerne.</p>
        
        <div class="amount">
            Montant: {data.get('total_amount', 'N/A')} {data.get('invoice', {}).get('currency', 'TND')}
        </div>
        
        <p>Veuillez vous connecter à votre espace client pour plus de détails.</p>
    </div>
    
    <div class="footer">
        <p>Cet email a été envoyé automatiquement par le système FlowERP</p>
        <p>© {datetime.now().year} FlowERP - Tous droits réservés</p>
    </div>
</body>
</html>
"""

    def test_connection(self):
        """Tester la connexion SMTP"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Test de connexion SMTP échoué: {e}")
            return False

    def get_email_stats(self, category=None, days=30):
        """
        Récupérer les statistiques d'envoi d'emails
        (À implémenter avec une base de données de tracking)
        """
        # Placeholder pour les statistiques
        return {
            'sent_today': 0,
            'sent_this_week': 0,
            'open_rate': 0,
            'click_rate': 0,
            'bounce_rate': 0
        }


# Alias pour la compatibilité
EmailService = AdvancedEmailService