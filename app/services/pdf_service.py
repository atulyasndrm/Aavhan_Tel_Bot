import io
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def safe_text(text, max_len=40):
    """Safely encodes text to prevent PDF rendering crashes from emojis/special chars."""
    if not text:
        return "N/A"
    t = str(text).replace("\n", " ").strip()
    t = t.encode('latin-1', 'replace').decode('latin-1')
    return t[:max_len] + "..." if len(t) > max_len else t

def generate_jobs_pdf(jobs):
    buffer = io.BytesIO()
    # Landscape orientation gives us more room for wide tables
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center align
    
    elements.append(Paragraph("Aavhan Master Jobs Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Group jobs by their current status
    grouped_jobs = {}
    for job in jobs:
        status = job.get('status', 'unknown').upper()
        if status not in grouped_jobs:
            grouped_jobs[status] = []
        grouped_jobs[status].append(job)
        
    for status, s_jobs in grouped_jobs.items():
        elements.append(Paragraph(f"Status: {status} ({len(s_jobs)} jobs)", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Table Header
        data = [["Title / Ceremony", "Date & Time", "Location", "Dakshina", "Priest ID"]]
        
        for job in s_jobs:
            title = safe_text(job.get('title') or job.get('ceremony_type'))
            dt = safe_text(f"{job.get('date', '')} {job.get('time', '')}")
            loc = safe_text(job.get('city') or job.get('location'))
            fees = safe_text(job.get('fees'))
            priest = safe_text(job.get('assigned_priest') or 'None')
            
            data.append([title, dt, loc, fees, priest])
        
        # Table Styling matching your orange/warm themes
        table = Table(data, colWidths=[160, 140, 160, 90, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F97316")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF9F2")),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (4, -1), 'CENTER'), # Center align fees and ID
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 25))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def generate_priests_pdf(users):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center align
    
    elements.append(Paragraph("Aavhan Master Priests Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Group priests by their verification status
    grouped_users = {}
    for user in users:
        status = user.get('verification_status', 'unknown').upper()
        if status not in grouped_users:
            grouped_users[status] = []
        grouped_users[status].append(user)
        
    for status, s_users in grouped_users.items():
        elements.append(Paragraph(f"Status: {status} ({len(s_users)} Priests)", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Table Header
        data = [["Priest ID", "Name", "Phone", "Role", "Joined At"]]
        
        for user in s_users:
            uid = safe_text(user.get('id'))
            name = safe_text(user.get('name'))
            phone = safe_text(user.get('phone'))
            role = safe_text(user.get('role', 'priest').capitalize())
            
            created_val = user.get('created_at')
            if created_val:
                created_str = created_val if isinstance(created_val, str) else created_val.strftime('%Y-%m-%d %H:%M')
            else:
                created_str = 'N/A'
            created = safe_text(created_str)
            
            data.append([uid, name, phone, role, created])
        
        # Table Styling matching a blue/cool theme for users
        table = Table(data, colWidths=[120, 200, 140, 100, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#EFF6FF")),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'), # Center align ID
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 25))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()