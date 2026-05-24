import io
from datetime import datetime, timedelta
from collections import defaultdict

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from app.db.postgres import db_pool

async def generate_analytics_image():
    # 1. Fetch data from DB
    async with db_pool.acquire() as conn:
        priests_data = await conn.fetch("""
            SELECT verification_status, COUNT(*) as count 
            FROM users 
            GROUP BY verification_status
        """)
        
        jobs_data = await conn.fetch("""
            SELECT DATE(created_at) as day, COUNT(*) as count 
            FROM bookings 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY day
            ORDER BY day
        """)

    # 2. Process Priest Data (Pie Chart)
    status_counts = {'approved': 0, 'pending': 0, 'rejected': 0}
    for row in priests_data:
        status_counts[row['verification_status']] = row['count']
        
    labels = ['Verified', 'Pending', 'Rejected']
    sizes = [status_counts['approved'], status_counts['pending'], status_counts['rejected']]
    colors = ['#22C55E', '#F59E0B', '#EF4444']  # Green, Yellow, Red

    # 3. Process Jobs Data (Bar Chart)
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    jobs_by_day = defaultdict(int)
    
    for row in jobs_data:
        day_val = row['day']
        if day_val:
            # Safely handle both string and date objects
            day_str = day_val if isinstance(day_val, str) else day_val.strftime('%Y-%m-%d')
            jobs_by_day[day_str] += row['count']
        
    job_counts = [jobs_by_day[d] for d in days]
    short_days = [datetime.strptime(d, '%Y-%m-%d').strftime('%b %d') for d in days]

    # 4. Draw the Plot
    fig = Figure(figsize=(14, 6))
    canvas = FigureCanvas(fig)
    ax1, ax2 = fig.subplots(1, 2)
    
    fig.suptitle('Aavhan Platform Analytics', fontsize=18, fontweight='bold', color='#111827')

    # Plot Pie Chart
    if sum(sizes) == 0:
        ax1.text(0.5, 0.5, "No Priests Found", ha='center', fontsize=12)
    else:
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140, textprops={'color': '#374151', 'weight': 'bold'})
    ax1.set_title('Priest Network Status', color='#4B5563', pad=15, fontsize=14, fontweight='bold')

    # Plot Bar Chart
    bars = ax2.bar(short_days, job_counts, color='#F97316', edgecolor='#C2410C', linewidth=1.5, width=0.5)
    ax2.set_title('Jobs Created (Last 7 Days)', color='#4B5563', pad=15, fontsize=14, fontweight='bold')
    ax2.tick_params(axis='x', rotation=30)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Add exact numbers above the bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax2.annotate(f'{height}', xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 4), textcoords="offset points",
                         ha='center', va='bottom', fontweight='bold', color='#111827')

    fig.tight_layout()
    
    # 5. Export to Image Buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FFF9F2')
    buf.seek(0)
    
    return buf.getvalue()