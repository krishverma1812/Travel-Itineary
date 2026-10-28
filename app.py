import streamlit as st
import json
import random
import io
import datetime
from typing import Dict, List, Any, Optional
from fpdf import FPDF
import google.generativeai as genai

# ==========================================
# PAGE CONFIGURATION & WANDERLUST STYLING
# ==========================================
st.set_page_config(
    page_title="RoamCraft - AI Travel Itinerary Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Global Styling */
    .stApp {
        background-color: #F8FAFC;
    }
    h1, h2, h3 {
        color: #0F172A;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #0EA5E9 0%, #3B82F6 50%, #6366F1 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(14, 165, 233, 0.3);
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF !important;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.95;
        margin-top: 0.5rem;
    }

    /* Cards & Containers */
    .travel-card {
        background-color: #FFFFFF;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    
    /* Vibe Pills */
    .vibe-tag {
        display: inline-block;
        background-color: #E0F2FE;
        color: #0369A1;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Slot Headers */
    .slot-title {
        font-weight: 700;
        color: #1E293B;
        margin-top: 0.75rem;
    }
    .slot-time {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }

    /* Currency Badge */
    .currency-badge {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "saved_trips" not in st.session_state:
    st.session_state.saved_trips = {}
if "current_itinerary" not in st.session_state:
    st.session_state.current_itinerary = None
if "recommended_destinations" not in st.session_state:
    st.session_state.recommended_destinations = []

# ==========================================
# MOCK / FALLBACK ENGINE DATA (DEMO MODE)
# ==========================================
MOCK_RECOMMENDATIONS = {
    "Beach": [
        {"city": "Bali, Indonesia", "season": "Dry Season (Apr-Oct)", "tags": ["Surfing", "Temples", "Tropical"], "estimated_daily_usd": 65},
        {"city": "Cancun, Mexico", "season": "Winter Sunshine (Nov-Apr)", "tags": ["Resorts", "Mayan Ruins", "Nightlife"], "estimated_daily_usd": 120},
        {"city": "Phuket, Thailand", "season": "Cool Season (Nov-Feb)", "tags": ["Islands", "Street Food", "Beaches"], "estimated_daily_usd": 55}
    ],
    "Mountains": [
        {"city": "Banff, Canada", "season": "Summer Hikes (Jun-Aug)", "tags": ["Lakes", "Glaciers", "Wildlife"], "estimated_daily_usd": 180},
        {"city": "Interlaken, Switzerland", "season": "Spring/Summer (May-Sep)", "tags": ["Alps", "Hiking", "Adventure"], "estimated_daily_usd": 220},
        {"city": "Manali, India", "season": "Summer Escape (Mar-Jun)", "tags": ["Peaks", "Passes", "Trekking"], "estimated_daily_usd": 40}
    ],
    "Cultural": [
        {"city": "Kyoto, Japan", "season": "Cherry Blossom (Mar-May)", "tags": ["Shrines", "Tea Ceremonies", "Gardens"], "estimated_daily_usd": 140},
        {"city": "Rome, Italy", "season": "Shoulder Season (Apr-May)", "tags": ["History", "Architecture", "Gelato"], "estimated_daily_usd": 160},
        {"city": "Varanasi, India", "season": "Winter Months (Oct-Mar)", "tags": ["Ghats", "Spiritual", "Heritage"], "estimated_daily_usd": 30}
    ],
    "Urban": [
        {"city": "Tokyo, Japan", "season": "Autumn Foliage (Oct-Nov)", "tags": ["Tech", "Foodie", "Shopping"], "estimated_daily_usd": 150},
        {"city": "New York City, USA", "season": "Autumn (Sep-Nov)", "tags": ["Broadway", "Skyscrapers", "Museums"], "estimated_daily_usd": 250},
        {"city": "London, UK", "season": "Summer (Jun-Aug)", "tags": ["Parks", "West End", "Royalty"], "estimated_daily_usd": 200}
    ]
}

def generate_mock_day_plan(day_num: int, city: str, budget: str) -> Dict[str, Any]:
    multiplier = 1.0 if budget == "Budget" else (1.8 if budget == "Moderate" else 3.5)
    clusters = [
        "Downtown Historic Core", 
        "Arts & Museum District", 
        "Waterfront & Port Zone", 
        "Northern Hills & Parks"
    ]
    cluster_name = clusters[(day_num - 1) % len(clusters)]
    
    return {
        "day": day_num,
        "geographic_cluster": cluster_name,
        "morning": {
            "title": f"Explore {cluster_name} Key Landmarks",
            "description": f"Morning walking tour around famous heritage sites in {cluster_name}.",
            "cost_usd": round(15 * multiplier, 2)
        },
        "lunch": {
            "title": f"Local Cuisine at {cluster_name} Bistro",
            "description": "Authentic regional lunch featuring local specialties.",
            "cost_usd": round(20 * multiplier, 2)
        },
        "afternoon": {
            "title": f"{cluster_name} Cultural Experience",
            "description": "Visit top-rated local art galleries, gardens, or street markets.",
            "cost_usd": round(25 * multiplier, 2)
        },
        "evening": {
            "title": f"Dinner & Evening Lights in {cluster_name}",
            "description": "Scenic dinner followed by live local acoustic music or night view.",
            "cost_usd": round(40 * multiplier, 2)
        }
    }

# ==========================================
# LLM SERVICE INTEGRATION ENGINE
# ==========================================
def call_llm(prompt: str, api_key: str) -> Optional[str]:
    """Helper to query Gemini API safely with exception handling."""
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {e}. Falling back to smart mock engine.")
        return None

# ==========================================
# PDF GENERATION ENGINE
# ==========================================
class ItineraryPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(14, 165, 233)
        self.cell(0, 10, 'ROAMCRAFT TRAVEL GUIDE', border=False, ln=True, align='C')
        self.set_draw_color(226, 232, 240)
        self.line(10, 22, 200, 22)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf_itinerary(itinerary_data: Dict[str, Any]) -> bytes:
    pdf = ItineraryPDF()
    pdf.add_page()
    
    # Title Section
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, f"Trip to {itinerary_data.get('destination', 'Your Trip')}", ln=True)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    metadata_str = f"Duration: {itinerary_data.get('duration')} Days | Party: {itinerary_data.get('party')} | Pace: {itinerary_data.get('pace')} | Budget: {itinerary_data.get('budget')}"
    pdf.cell(0, 6, metadata_str, ln=True)
    pdf.ln(5)

    # Days Loop
    days = itinerary_data.get("days", [])
    total_cost = 0.0
    
    for d in days:
        pdf.set_fill_color(224, 242, 254)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(3, 105, 161)
        pdf.cell(0, 8, f" Day {d['day']} - Cluster: {d.get('geographic_cluster', 'N/A')}", ln=True, fill=True)
        pdf.ln(2)

        for slot_key, slot_name in [("morning", "Morning"), ("lunch", "Lunch"), ("afternoon", "Afternoon"), ("evening", "Evening")]:
            slot = d.get(slot_key, {})
            title = slot.get("title", "N/A")
            desc = slot.get("description", "")
            cost = slot.get("cost_usd", 0.0)
            total_cost += cost

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(35, 6, f"{slot_name}:", ln=False)
            pdf.cell(0, 6, f"{title} (${cost:.2f})", ln=True)
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 5, desc)
            pdf.ln(1)
        pdf.ln(4)

    # Emergency Contact Checklist
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Emergency Checklist & Key Contacts", ln=True)
    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    checklist = [
        "[ ] Local Emergency Hotline (Police/Ambulance)",
        "[ ] Nearest Embassy / Consulate Contact Info",
        "[ ] Comprehensive Travel Insurance Policy Details",
        "[ ] Digital & Printed Copies of Passport / Visa",
        "[ ] Hotel Reservations & Airport Transfer Vouchers",
        "[ ] Local SIM Card or International Roaming Active"
    ]
    for chk in checklist:
        pdf.cell(0, 7, chk, ln=True)

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Estimated Cumulative Budget: ${total_cost:.2f} USD", ln=True)

    return bytes(pdf.output())

# ==========================================
# APP LAYOUT: SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.markdown("## ⚙️ Config & Preferences")

api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Leave blank for Demo Mode (Mock Engine)")
demo_mode = not bool(api_key)

if demo_mode:
    st.sidebar.info("💡 **Demo Mode Active**: Using built-in intelligent mock engine.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Trip Parameters")

destination_mode = st.sidebar.radio("Destination Selection", ["Fixed Destination", "Open-Ended Vibe"])
if destination_mode == "Fixed Destination":
    target_destination = st.sidebar.text_input("Enter City/Country", value="Tokyo, Japan")
    open_vibe = None
else:
    target_destination = ""
    open_vibe = st.sidebar.selectbox("Select Trip Vibe", ["Beach", "Mountains", "Cultural", "Urban"])

trip_duration = st.sidebar.slider("Trip Duration (Days)", min_value=1, max_value=7, value=3)
start_date = st.sidebar.date_input("Travel Start Date", datetime.date.today() + datetime.timedelta(days=14))
budget_level = st.sidebar.selectbox("Budget Level", ["Budget", "Moderate", "Luxury"], index=1)
travel_party = st.sidebar.selectbox("Travel Party", ["Solo", "Couple", "Family", "Friends"])
travel_pace = st.sidebar.select_slider("Travel Pace", options=["Relaxed", "Moderate", "Fast-Paced"], value="Moderate")
selected_interests = st.sidebar.multiselect(
    "Interests", 
    ["Food", "Adventure", "History", "Nightlife", "Shopping", "Relaxation"],
    default=["Food", "History"]
)

currency_display = st.sidebar.selectbox("Currency Display Mode", ["USD ($)", "INR (₹)"])
fx_rate = 83.0 if "INR" in currency_display else 1.0
curr_symbol = "₹" if "INR" in currency_display else "$"

# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">✈️ RoamCraft Itinerary Planner</div>
    <div class="hero-subtitle">Geographically clustered, AI-optimized day-by-day travel itineraries with dynamic vibe tuning.</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "💡 Smart Recommender", 
    "🗺️ Day-by-Day Plan", 
    "🎨 Dynamic Activity Swap", 
    "📁 Trip Management & PDF"
])

# ------------------------------------------
# TAB 1: SMART DESTINATION RECOMMENDER
# ------------------------------------------
with tab1:
    st.markdown("### 🌟 Smart Destination Recommender")
    st.write("Discover tailored cities matching your travel vibe, budget level, and preferred season.")
    
    col_rec1, col_rec2 = st.columns([1, 3])
    with col_rec1:
        vibe_query = st.selectbox("Explore Vibe Category", ["Beach", "Mountains", "Cultural", "Urban"], index=0)
        rec_button = st.button("🔎 Get Recommendations", use_container_width=True)
        
    with col_rec2:
        if rec_button or st.session_state.recommended_destinations:
            if rec_button:
                if not demo_mode:
                    prompt = f"Recommend top 3 travel destinations for vibe '{vibe_query}' with budget '{budget_level}'. Return strictly raw JSON array with fields: city, season, tags (array), estimated_daily_usd (number)."
                    response = call_llm(prompt, api_key)
                    try:
                        st.session_state.recommended_destinations = json.loads(response)
                    except Exception:
                        st.session_state.recommended_destinations = MOCK_RECOMMENDATIONS.get(vibe_query, [])
                else:
                    st.session_state.recommended_destinations = MOCK_RECOMMENDATIONS.get(vibe_query, [])

            for rec in st.session_state.recommended_destinations:
                daily_cost = rec.get("estimated_daily_usd", 100) * fx_rate
                st.markdown(f"""
                <div class="travel-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">📍 {rec['city']}</h3>
                        <span class="currency-badge">~{curr_symbol}{daily_cost:.0f} / day</span>
                    </div>
                    <p style="margin: 0.5rem 0; color: #475569;"><b>Best Season:</b> {rec.get('season', 'Year Round')}</p>
                    <div>
                        {''.join([f'<span class="vibe-tag">{tag}</span>' for tag in rec.get('tags', [])])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: DAY-BY-DAY ITINERARY GENERATOR
# ------------------------------------------
with tab2:
    st.markdown("### 🗺️ Day-by-Day Geographically Clustered Plan")
    
    generate_col1, generate_col2 = st.columns([3, 1])
    with generate_col1:
        st.write(f"Generate plan for **{target_destination if target_destination else 'Open Vibe Trip'}** ({trip_duration} Days, {budget_level} budget)")
    with generate_col2:
        btn_generate = st.button("🚀 Generate Itinerary", type="primary", use_container_width=True)

    if btn_generate:
        dest_name = target_destination if target_destination else (open_vibe + " Destination")
        
        with st.spinner("Clustering attractions geographically & balancing transit times..."):
            if not demo_mode:
                prompt = f"""
                Create a {trip_duration}-day detailed itinerary for {dest_name}.
                Travel Party: {travel_party}, Pace: {travel_pace}, Budget: {budget_level}, Interests: {', '.join(selected_interests)}.
                Return ONLY valid JSON with format:
                {{
                    "destination": "{dest_name}",
                    "days": [
                        {{
                            "day": 1,
                            "geographic_cluster": "District Name",
                            "morning": {{"title": "", "description": "", "cost_usd": 20.0}},
                            "lunch": {{"title": "", "description": "", "cost_usd": 15.0}},
                            "afternoon": {{"title": "", "description": "", "cost_usd": 25.0}},
                            "evening": {{"title": "", "description": "", "cost_usd": 40.0}}
                        }}
                    ]
                }}
                """
                resp = call_llm(prompt, api_key)
                try:
                    clean_resp = resp.strip().replace("```json", "").replace("```", "")
                    parsed = json.loads(clean_resp)
                    parsed["duration"] = trip_duration
                    parsed["budget"] = budget_level
                    parsed["party"] = travel_party
                    parsed["pace"] = travel_pace
                    st.session_state.current_itinerary = parsed
                except Exception:
                    days_data = [generate_mock_day_plan(i + 1, dest_name, budget_level) for i in range(trip_duration)]
                    st.session_state.current_itinerary = {
                        "destination": dest_name, "duration": trip_duration, "budget": budget_level,
                        "party": travel_party, "pace": travel_pace, "days": days_data
                    }
            else:
                days_data = [generate_mock_day_plan(i + 1, dest_name, budget_level) for i in range(trip_duration)]
                st.session_state.current_itinerary = {
                    "destination": dest_name, "duration": trip_duration, "budget": budget_level,
                    "party": travel_party, "pace": travel_pace, "days": days_data
                }

    if st.session_state.current_itinerary:
        itin = st.session_state.current_itinerary
        st.success(f"Itinerary active for **{itin['destination']}**!")
        
        cumulative_cost = 0.0
        for day_plan in itin["days"]:
            day_num = day_plan["day"]
            cluster = day_plan.get("geographic_cluster", "Central Zone")
            
            with st.expander(f"🗓️ Day {day_num}: {cluster}", expanded=True):
                col_slots = st.columns(4)
                slots = [("Morning", "morning", "🌅"), ("Lunch", "lunch", "🍱"), ("Afternoon", "afternoon", "🏛️"), ("Evening", "evening", "🌙")]
                
                for idx, (slot_label, slot_key, icon) in enumerate(slots):
                    slot_data = day_plan.get(slot_key, {})
                    cost_val = slot_data.get("cost_usd", 0.0) * fx_rate
                    cumulative_cost += slot_data.get("cost_usd", 0.0)
                    
                    with col_slots[idx]:
                        st.markdown(f"**{icon} {slot_label}**")
                        st.markdown(f"##### {slot_data.get('title', 'N/A')}")
                        st.caption(slot_data.get("description", ""))
                        st.markdown(f"**Cost:** `{curr_symbol}{cost_val:.2f}`")

        st.markdown("---")
        total_disp = cumulative_cost * fx_rate
        st.metric(label=f"Total Estimated Budget ({currency_display.split()[0]})", value=f"{curr_symbol}{total_disp:,.2f}")

# ------------------------------------------
# TAB 3: VIBE CUSTOMIZATION & SINGLE-DAY SWAP
# ------------------------------------------
with tab3:
    st.markdown("### 🎨 Vibe Customization & Dynamic Activity Swap")
    st.write("Modify a specific day's activities based on custom prompts without erasing the rest of your itinerary.")
    
    if not st.session_state.current_itinerary:
        st.warning("Please generate an itinerary in Tab 2 first.")
    else:
        current_days = [d["day"] for d in st.session_state.current_itinerary["days"]]
        selected_day = st.selectbox("Select Day to Modify", current_days)
        swap_instruction = st.text_input(
            "Swap Request / Vibe Change", 
            placeholder="e.g., Replace museum with outdoor food market, find vegetarian dining."
        )
        
        if st.button("🔄 Regenerate Selected Day"):
            if swap_instruction:
                with st.spinner(f"Updating Day {selected_day}..."):
                    day_idx = selected_day - 1
                    dest = st.session_state.current_itinerary["destination"]
                    
                    if not demo_mode:
                        prompt = f"""
                        Regenerate ONLY Day {selected_day} for trip to {dest}.
                        Modification requirement: '{swap_instruction}'.
                        Return raw JSON object matching:
                        {{
                            "day": {selected_day},
                            "geographic_cluster": "Updated Cluster",
                            "morning": {{"title": "", "description": "", "cost_usd": 20.0}},
                            "lunch": {{"title": "", "description": "", "cost_usd": 15.0}},
                            "afternoon": {{"title": "", "description": "", "cost_usd": 25.0}},
                            "evening": {{"title": "", "description": "", "cost_usd": 40.0}}
                        }}
                        """
                        resp = call_llm(prompt, api_key)
                        try:
                            clean_resp = resp.strip().replace("```json", "").replace("```", "")
                            updated_day = json.loads(clean_resp)
                            st.session_state.current_itinerary["days"][day_idx] = updated_day
                            st.success(f"Day {selected_day} successfully updated!")
                        except Exception:
                            # Demo fallback alteration
                            st.session_state.current_itinerary["days"][day_idx]["morning"]["title"] = f"Custom: {swap_instruction[:20]}..."
                            st.session_state.current_itinerary["days"][day_idx]["morning"]["description"] = f"Adapted morning activity to match: '{swap_instruction}'"
                            st.success(f"Day {selected_day} updated via smart fallback engine!")
                    else:
                        st.session_state.current_itinerary["days"][day_idx]["morning"]["title"] = f"Custom: {swap_instruction[:20]}..."
                        st.session_state.current_itinerary["days"][day_idx]["morning"]["description"] = f"Adapted morning activity to match: '{swap_instruction}'"
                        st.success(f"Day {selected_day} updated via smart fallback engine!")

# ------------------------------------------
# TAB 4: TRIP MANAGEMENT & PDF EXPORT
# ------------------------------------------
with tab4:
    st.markdown("### 📁 Trip Management & Offline Export")
    
    if st.session_state.current_itinerary:
        col_mgt1, col_mgt2 = st.columns(2)
        
        with col_mgt1:
            st.markdown("#### 💾 Save Current Itinerary")
            trip_title = st.text_input("Trip Label", value=f"{st.session_state.current_itinerary['destination']} Getaway")
            if st.button("Save to History"):
                st.session_state.saved_trips[trip_title] = st.session_state.current_itinerary.copy()
                st.success(f"Saved '{trip_title}' to trip history!")
        
        with col_mgt2:
            st.markdown("#### 📄 Export Offline Travel Guide")
            pdf_bytes = generate_pdf_itinerary(st.session_state.current_itinerary)
            st.download_button(
                label="📥 Download PDF Travel Guide",
                data=pdf_bytes,
                file_name=f"{st.session_state.current_itinerary['destination'].lower().replace(' ', '_')}_itinerary.pdf",
                mime="application/pdf"
            )

    st.markdown("---")
    st.markdown("#### 📜 Saved Trips History")
    if not st.session_state.saved_trips:
        st.info("No saved trips yet. Save a trip above to manage history.")
    else:
        for title, trip_data in st.session_state.saved_trips.items():
            with st.expander(f"✈️ {title} ({trip_data.get('duration')} Days)"):
                st.json(trip_data)
                if st.button(f"Load '{title}' into Planner", key=f"load_{title}"):
                    st.session_state.current_itinerary = trip_data
                    st.rerun()