from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from xml.sax.saxutils import escape
from Monthly_Return_Analysis_Fourthstone import get_tearsheet_data, get_updown_data

#powershell: .\.venv\Scripts\Activate.ps1

primary_color = colors.HexColor("#350B4D")
text_muted = colors.HexColor("#5A1F78")
line_color = colors.HexColor("#E5A93B")



class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically calculate the total page count
    and render a uniform header and footer across all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Save state for the second pass
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        page_width, page_height = self._pagesize
        left_edge = 54
        right_edge = page_width - 54
        header_rule_y = page_height - 54
        header_text_y = page_height - 46
        
        # ----------------- RUNNING HEADER -----------------
        self.setStrokeColor(line_color)
        self.setLineWidth(0.75)
        # Top Rule Accent
        self.line(left_edge, header_rule_y, right_edge, header_rule_y)
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(primary_color)
        self.drawString(
            left_edge,
            header_text_y,
            "Radar Fund Research | 804 Sample St | Example Only"
        )

        # --- Scaled & Centered Square Image ---
        image_path = r"C:\GithubLocalDirectory\ReportLab_Items\radar_header_3.png"
        img_size = 35
        center_x = (page_width - img_size) / 2
        image_y = page_height - 50
        
        self.drawImage(image_path, center_x, image_y, width=img_size, height=img_size, preserveAspectRatio=True, mask='auto')
        # --------------------------------------
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(primary_color)
        self.drawRightString(
            right_edge,
            header_text_y,
            "Jack Kanehann, CFA | jackkanehann@gmail.com"
        )
    
        
        # ----------------- RUNNING FOOTER -----------------
        # Bottom Rule Accent
        self.line(left_edge, 54, right_edge, 54)
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#9B2C2C")) # Subtle Crimson for Disclaimer
        self.drawString(left_edge, 42, "STRICTLY CONFIDENTIAL")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(text_muted)
        self.drawString(170, 42, "FOR INTERNAL USE ONLY")
        
        # Dynamic Page Numbers (e.g., "Page 1 of 3")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(right_edge, 42, page_str)
        
        self.restoreState()


def build_appendix_table(table_data, header_style, metric_style, cell_style, available_width):
    """Convert exported rows into a readable, full-width landscape table."""
    formatted_rows = []
    for row_index, row in enumerate(table_data):
        formatted_row = []
        for column_index, value in enumerate(row):
            if row_index == 0:
                style = header_style
            elif column_index == 0:
                style = metric_style
            else:
                style = cell_style
            formatted_row.append(Paragraph(escape(str(value)), style))
        formatted_rows.append(formatted_row)

    metric_width = 155
    value_width = (available_width - metric_width) / (len(formatted_rows[0]) - 1)
    appendix_table = Table(
        formatted_rows,
        colWidths=[metric_width] + [value_width] * (len(formatted_rows[0]) - 1),
        repeatRows=1
    )
    appendix_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor("#EDF2F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.65, colors.HexColor("#718096")),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor("#1A202C")),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    return appendix_table


def build_metric_definitions_table(
    table_data,
    header_style,
    metric_style,
    definition_style,
    available_width
):
    """Build the Appendix D metric glossary and formula table."""
    formatted_rows = []
    for row_index, row in enumerate(table_data):
        formatted_row = []
        for column_index, value in enumerate(row):
            if row_index == 0:
                style = header_style
            elif column_index == 0:
                style = metric_style
            else:
                style = definition_style
            formatted_row.append(Paragraph(escape(str(value)), style))
        formatted_rows.append(formatted_row)

    metric_width = 135
    definition_width = 310
    formula_width = available_width - metric_width - definition_width
    definitions_table = Table(
        formatted_rows,
        colWidths=[metric_width, definition_width, formula_width],
        repeatRows=1
    )
    definitions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor("#EDF2F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.65, colors.HexColor("#718096")),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor("#1A202C")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
    ]))
    return definitions_table


def create_hedge_fund_report(output_filename="hedge_fund_report.pdf"):
    portrait_size = letter
    landscape_size = landscape(letter)
    doc = BaseDocTemplate(output_filename, pagesize=portrait_size)
    portrait_frame = Frame(
        54, 72,
        portrait_size[0] - 108,
        portrait_size[1] - 144,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id='PortraitFrame'
    )
    landscape_frame = Frame(
        54, 72,
        landscape_size[0] - 108,
        landscape_size[1] - 144,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id='LandscapeFrame'
    )
    doc.addPageTemplates([
        PageTemplate(
            id='Portrait',
            pagesize=portrait_size,
            frames=[portrait_frame]
        ),
        PageTemplate(
            id='Landscape',
            pagesize=landscape_size,
            frames=[landscape_frame]
        ),
    ])
    
    styles = getSampleStyleSheet()
    
    # Custom Typography Styles matching Institutional Tier Layouts
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
            'SectionH1',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1A365D"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=10
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=0 # Left-align
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748"),
        alignment=0 #1 =  Centered
    )

    table_cell_style_2 = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748"),
            alignment=0 # Centered
        )

    appendix_title_style = ParagraphStyle(
        'AppendixTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceAfter=10
    )

    appendix_header_style = ParagraphStyle(
        'AppendixHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=9.5,
        textColor=colors.white,
        alignment=1
    )

    appendix_metric_style = ParagraphStyle(
        'AppendixMetric',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor("#111827"),
        alignment=0
    )

    appendix_cell_style = ParagraphStyle(
        'AppendixCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor("#111827"),
        alignment=1
    )

    appendix_definition_style = ParagraphStyle(
        'AppendixDefinition',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#111827"),
        alignment=0
    )

    appendix_note_style = ParagraphStyle(
        'AppendixNote',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8
    )

    story = []
    
    # ------------------ PAGE 1: TITLE & EXECUTIVE SUMMARY ------------------
    story.append(Paragraph("Fourthstone Opportunity Fund", title_style))
    story.append(Paragraph("L/S Opportunistic Bank Equity Manager | Data as of 7/31/2026", subtitle_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Recommendation and Summary", h1_style))
    recommendation_text = (
    "We recommend a 2% portfolio allocation to Fourthstone's flagship opportunity fund, assuming a 40% portfolio allocation to public equities. "
    "Fourthstone's differentiated research process leads to an informational edge over other market participants in the small-cap bank equity space. "
    "Their track record shows net benchmark outperformance 10 out of 12 years from 2014 to 2025, with an annualized alpha of 14.9% over that period. "
    "The fund has returned 19.4% annualized since inception, compared to 7.1% for the Nasdaq Bank Index and 14.6% for the S&amp;P 500. " \
    "Their short positions have yielded a positive absolute return in 7 out of 12 years."  
    )
    story.append(Paragraph(recommendation_text, body_style))

    summary_text = ( 
    "The fund's investment universe is the roughly 630 publicly traded bank common stocks, with a focus on the micro-to-mid-cap area. "
    "This subset of the bank equity universe is a poor fit for larger funds due to onerous trading and reporting restrictions once you cross a 10% ownership threshold. "
    "Accordingly, this universe lacks robust sell-side coverage, creating an ongoing opportunity for Fourthstone's research and trading apparatus. " \
    "Their research synthesizes quantitative balance sheet data from regulatory disclosures with fundamental analysis and due diligence on commercial banks and macroeconomic trends "
    "to inform portfolio positions and net exposure. " \
    "The fund may opportunistically invest in financial service companies tangential to the commercial banking industry, including fintechs, REITs, home builders, BDCs, and peer-to-peer lenders."
    )
    story.append(Paragraph(summary_text, body_style))
    
    # Financial Metrics Quick Table
    story.append(Spacer(1, 10))
    terms_data = [
        [Paragraph("<b>Key Terms</b>", table_header_style), Paragraph("<b></b>", table_header_style),  Paragraph("<b>Service Providers</b>", table_header_style), Paragraph("<b></b>", table_header_style), ],
        [Paragraph("Minimum Subscription", table_cell_style), Paragraph("$1,000,000", table_cell_style_2), Paragraph("Auditor", table_cell_style), Paragraph("KPMG", table_cell_style)],
        [Paragraph("Management Fee", table_cell_style), Paragraph("2%", table_cell_style), Paragraph("Custodians", table_cell_style), Paragraph("Wells Fargo & Jeffries", table_cell_style)],
        [Paragraph("Incentive Fee", table_cell_style), Paragraph("20%", table_cell_style), Paragraph("Prime Brokers", table_cell_style), Paragraph("Wells Fargo & Jeffries", table_cell_style)],
        [Paragraph("High Water Mark", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Administrator", table_cell_style), Paragraph("SS&amp;C", table_cell_style)],
        [Paragraph("Gate", table_cell_style), Paragraph("No", table_cell_style), Paragraph("Onshore Legal", table_cell_style), Paragraph("Faegre Drinker Biddle & Reath LLP", table_cell_style)],
        [Paragraph("Subcriptions / Redemptions", table_cell_style), Paragraph("Monthly / Quarterly with 60 days notice", table_cell_style), Paragraph("Offshore Legal", table_cell_style), Paragraph("Maples & Calder", table_cell_style)],
        [Paragraph("Lock Up", table_cell_style), Paragraph("1 Year Soft-Lock; 5% Withdrawal Penalty", table_cell_style), Paragraph("Compliance", table_cell_style), Paragraph("IQ-EQ Fund Services", table_cell_style)],
        [Paragraph("Investor Communications", table_cell_style), Paragraph("Monthly", table_cell_style), Paragraph("Technology", table_cell_style), Paragraph("Align Communications", table_cell_style)]
    ]
    
    # Widths must sum up to total drawable space: 612 (letter width) - 108 (margins) = 504
    terms_table = Table(terms_data, colWidths=[126, 126, 126, 126])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F7FAFC"), colors.white]),
        #('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(terms_table)

    story.append(PageBreak())

    story.append(Paragraph("Firm Overview", h1_style))
    overview_text = (
        "Fourthstone LLC is a registered investment advisor to financial sector equity strategies.  Their flagship Opportunity Fund employs variable net exposure targeting mid-teens net returns. "
        "Based in Louisville, MO, the firm was founded in 2014 by CIO and Managing Partner Phil Stone after he successfully ran a similar strategy as the CIO of a family office from 2010-2013. "
        "After first passing $100MM AUM in 2018, Fourthstone surpassed $1B AUM for the first time in 2026. " \
        "At the end of June 2026, firm AUM stood at $996MM, with $961MM deployed in the L/S strategy and $35MM in their long-only Small-Cap Financials Fund. "
        "The firm is 100% employee-owned, with Phil Stone retaining majority ownership. Internal capital comprises 9% of firm AUM." 
        )
    story.append(Paragraph(overview_text, body_style))

    overview2 = (
    
    "The firm employs 14 people, with 8 on the investment team and the remainder in operations and marketing. "
    "The marketing and investor relations function is led by CEO Amy Stone and VP of IR Rachael Turin, while operations and "
    "compliance are led by Rob Anderson, CFO and CCO. "
    "The investment team operates with a flat structure, with each research analyst and trader reporting directly to Phil Stone. " \
    "They aim to generate positive absolute returns in any market environment by investing long and short in US banks, thrifts, and related financial service equities. " \
    "They view their short book as a return and alpha generator, as opposed to a mere volatility or beta dampener."

    )

    story.append(Paragraph(overview2, body_style))

    story.append(Paragraph("Staff Overview<font size=12><sup><sup> 1</sup></sup></font>", h1_style))


    story.append(Paragraph("Phil Stone, Managing Partner", h2_style))
    person_text = (
            "Responsible for portfolio management and trading. Member of the Board of Directors and Chair of the Investment Committee. "
                    "Stone was previously Chief Investment Officer of Driven Capital Management, a family office managing a global portfolio of equities, fixed income, real estate and private equity holdings. "
                    "The core of this portfolio was the long/short financial sector strategy upon which Fourthstone was founded. "
                    "Stone was previously at The Observatory, a family office, and prior to that, was a bank equities analyst at a long/short financial sector hedge fund and a credit analyst at Mercantile Bank & Trust. " 
                    "Stone is a CFA® charterholder. "
                    "He graduated from Loyola College in Maryland with an MBA in Finance and from the University of Maryland with a Bachelor of Science in Economics. "
        )
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Grant Burtch, Senior Research Analyst", h2_style))
    person_text = (
            "Responsible for identification and analysis of potential portfolio investments. Burtch was previously Head Research Associate at Raymond James & Associates’ "
                "Chicago office responsible for covering more than 80 banks during the course of his tenure and managing a team of Research Associates. "
                "His nine-year tenure at Raymond James included conducting research on small- to large-cap banks located in the Midwest, Pacific Northwest, Southwest and West Coast. "
                "While at the firm, Burtch conducted non-deal road shows, research meetings with C-level bank executives and issued financial models, forecasts and industry reports for institutional clients. "
                "He is a CFA level II candidate and holds a Bachelor in Economics from the University of Michigan."
        )
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Jason Oetting, Senior Research Analyst", h2_style))
    person_text = (
             "Responsible for identification and analysis of potential portfolio investments.  Oetting re-joined Fourthstone after spending four years as a bank analyst at Millennium Management responsible for stock selection, portfolio construction and risk management.  "
                "Prior to joining Millennium, he was a Senior Analyst at Fourthstone and, prior to that, "
                "Oetting was VP of Equity Research and publishing analyst on the U.S. Mid- and Small-Cap Banks team at JP Morgan covering U.S. banks with market caps between $350 million to $26 billion.  "
                "Oetting previously served as Assistant VP on the insurance equity research team at FBR Capital Markets covering 25 companies.  Prior to that, he was a Mortgage Investor Reporting Analyst and a Post-Close Mortgage Auditor at Citigroup.  "
                "He has a Bachelor of Science in Managerial Economics from Washington University in St. Louis and a Master of Science in Accounting and Finance from the London School of Economics."
        )
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Ted Bade, Senior Research Analyst", h2_style))
    person_text = (
             "Responsible for identification and analysis of potential portfolio investments.  Prior to joining Fourthstone, Bade spent nine years as an Equity Research Analyst at Cannell Capital, where he helped manage a $700 million SMID-cap value hedge fund. "
                "While at Cannell Capital, Bade determined selection, timing and sizing of positions, maintained investment screens, and presented investment theses at annual investor conferences. "
                "Prior to joining Cannell Capital, he served as a Research Analyst for several buy-side firms, including Eidelman Virant and TurnMark Capital. "
                "Bade holds a Bachelor in History from Denison University."
        )
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Patrick Kelley, Senior Trader", h2_style))
    person_text = (
              "Responsible for the daily operation of Fourthstone’s equity trading, including best execution, technology and analytics.  Kelley brings twenty years trading experience to Fourthstone, including serving as Head Equity Trader for Kennedy Capital Management, "
                 "where he was responsible for overseeing the administration, technology, and the quality of broker execution for the trading department. At Kennedy, he was the principal Equity Trader for the Small Cap Value I, Small Cap Core, SMID Cap Value, SMID Cap Core, Mid Cap Value, and All Cap Value strategies. " 
                 "Kelley began his career as both a listed block trader and an OTC trader for KeyBanc Capital Markets in Cleveland, Ohio.  He holds a B.A.B.S. from Ohio University in Finance and Management Information Systems."
         )
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Amy Stone, CEO", h2_style))
    person_text = (
                 "Co-founder of the firm and member of the Board of Directors. Stone was previously VP of Strategy & Chief Marketing Officer for Save-A-Lot, a nearly $5bn retail chain. "
                    "Before joining Save-A-Lot, Stone led a performance improvement program across five continents and seven strategic performance units at BP, including the divestment of 50% of the company’s downstream US business. "
                    "Stone also held global IT, process improvement and procurement leadership positions at BP and Motorola. She began her career managing Fortune 100 public relations accounts at Magnet Communications. "
                    "Stone is a Board Member of Midwest BankCentre, a bank with assets exceeding $2bn, and was previously a Board Member of Relief International UK. "
                    "She holds a Bachelor of Arts in International Politics and Economics from Middlebury College."
            )   
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Rachael Turin, VP of Investor Relations", h2_style))
    person_text = (
            "Responsible for capital formation and investor relations.  Prior to joining Fourthstone, Turin was in charge of capital markets for The Rainier Companies, a large commercial real estate firm, and managed investor relations for Meridian Realty Advisors.  "
            "She is a graduate of The Real Estate Council’s Associate Leadership Council program and attended the University of Missouri – Columbia."
        )   
    story.append(Paragraph(person_text, body_style))
    story.append(Paragraph("Rob Anderson, CFO/CCO", h2_style))
    person_text = (
                "Responsible for finance, compliance, risk, and trade operations functions and a member of the Investment Committee. "
                "Anderson brings more than 30 years of experience with prior roles including Chief Financial Officer for PetSmart, the largest pet retailer in North America, and for Save-A-Lot, a nearly $5bn retail chain. " 
                "Prior to that he was the Principal Accounting Officer for Chipotle Mexican Grill, where he guided the company through a successful IPO, "
                "and spent more than a decade at McDonald’s Corporation in a variety of international postings as well as serving as the Head of Finance and Accounting for the company’s Partner Brands Group. "
                "Anderson is a Certified Public Accountant and has a Master’s degree in Finance from DePaul University.  He graduated from Northern Illinois University with a Bachelor of Science in Accountancy and is currently Treasurer for Habitat Humanity St Louis."
        )   
    story.append(Paragraph(person_text, body_style))

    # Force Multi-page Example to showcase Header/Footer behavior
    story.append(PageBreak())
    
    # ------------------ PAGE 2: RISK & ATTRIBUTION ------------------
    story.append(Paragraph("Investment Strategy", h1_style))
    story.append(Paragraph("Market Opportunity", h2_style))
    market_opp = (
        #em dash alt code 0151 "—" vs "--"
        "Commercial banks typically generate 70% to 90% of their total revenues from net interest income.  Micro-to-mid-cap banks are usually on the high side of this range. " \
        "A sizable portion of their remaining revenues are flat fees for ongoing service of deposits and loans, or one-time loan origination fees. All of these revenues are predicated on the bank's ability to "
        "prudently underwrite and originate loans while growing a sticky and low-interest-bearing deposit base.  This is the fundamental value proposition of a commercial bank—"
        "provide a safe place for businesses and consumers to deposit their capital and make money by lending capital at higher rates than you pay depositors. " \
        "While large commercial banks and investment banks have multiple business segments to generate revenue, "
        "Fourthstone focuses on regional commerical banks with a straightforward business model " \
        "because so much of the business value is derived directly from the balance sheet.  Knowing the business is knowing the balance sheet, and vice-versa. " \
        "Congruent business models across the industry make comparing valuation and growth prospects between banks relatively uncomplicated compared to other industries. "
        "Price to tangible book value (P/TBV) and return on tangible capital employed (ROTCE) are commonly used metrics to compare bank valuations and profitability." \
        "<br/>""<br/>"
        "A key advantage of the small cap bank equity market is the various bank holding and reporting restrictions.<sup>2</sup>  These restrictions become particularly onerous at the 10% ownership threshold, which " \
        "limits interest from institutional or generalist investors. A second-order effect of these restrictions is a broad lack of sell-side coverage—" \
        "59% of publicly traded banks have no sell-side coverage.  This broad, ongoing disinterest in the small cap bank area is a persistent opportunity for Fourthstone. " \
        "In addition to these special shareholder rules, commercial banks are subject to recurring balance sheet disclosure requirements.<sup>3</sup>  These various requirements can provide updates " \
        "on balance sheet health and positioning for the domestic banking industry as well as specific industry subsets grouped by geography, size, or other attributes.  "
        
    )
    story.append(Paragraph(market_opp, body_style))
    story.append(Paragraph("Research", h2_style))
    market_opp2 = (
        "Fourthstone's research aggregates information on commercial banks and their loan books to develop insights on broader economic trends and the commerical banking industry "
        "in addition to individual commercial banks. " \
        "The team is constantly updating their outlook on the sector, incorporating every new research note into forward estimates. " \
        "When new information becomes available, Fourthstone races to adjust their fair value estimates and trade accordingly before market prices can adjust. " \
        "They derive actionable investment theses from both quantitative and qualitative, fundamental analysis. " \
        "Fourthstone works to proactively understand how different banks will respond to a given industry catalyst. " \
        "With the proper preparation, they can generate returns by responding quickly to market developments instead of having to predict future events. " \
        "<br/>""<br/>"

        "Fourthstone looks to initiate positions when their fair value estimates are dislocated from current prices. " \
        "They look for a discrepancy of at least 20% between market price and fair value, most often measured in P/TBV multiples. " \
        "To make accurate projections of TBV, they need to understand the in-place balance sheet of the bank and how that balance sheet will evolve in the coming quarters and years. "
        "The in-place balance sheet will detail loan book diversification and credit or duration sensitivities. " \
        "Other fundamental indicators are absent from a single balance sheet, such as deposit quality, expected loan growth, and the rigor of a bank's underwriting process. " \
        "Evaluting a bank's prospects as a target of M&amp;A is important; "
        "the number of domestic commercial banks has trended downward for nearly 40 years as the industry consolidates.  "
        "Exogenous factors play a signficant role in projecting TBV growth.  "
        "Demographic changes and economic development can show where housing demand, and thus mortgage loans, are expected to grow. "
        "The regulatory environment may change capital requirements or remove barriers to bank acquisitons. "
        "Fourthstone's fair value projections consider all these details and more. "
        "To process available information efficiently, they begin with quantitative analysis of banks' regulatory data. " \
        "<br/>""<br/>"

        "Fourthstone aggregates and synthesizes data from banks' requisite regulatory filings as it is released. "
        "The data contained in these releases is voluminous. "
        "Asset and liability breakdowns detail bank and industry securities portfolios, deposit structures, and outstanding loans by amount outstanding and borrower type. "
        "Credit risk exhibits show past-due and non-accruing loans as well as loan charge offs and recoveries. " \
        "Income details in these filings include net interest income, fee income, operational overhead, and provision expenses. "
        "Quarterly average balances of deposits and loans, paired with NII data, show a given bank's effective yield paid to depositors and interest earned from loans. " \
        "It is critical to note that Fourthstone does not simply read through these reports. " \
        "They electronically digest, process, and synthesize the data from these reports and subsequently have the data at their fingertips. " \
        "Often, these reports are used to analyze industry or geographic trends by aggregating reports from a certain subset of individual banks. " \
        "Fourthstone relies on this wide data funnel and synthesis to effectively screen for investment ideas and areas of potential strength or vulnerability. "
        "<br/>""<br/>" \
        
        "Fourthstone's efficent processing of regulatory data provides a launchpad for their fundamental analysis.  "
        "Fourthstone seeks every incremental insight into the banks' deposit quality, underwriting culture, loan growth expectations, loan book diversification, "
        "balance sheet positioning, technology investment, anything that may affect future TBV.  " \
        "In pursuit of these incremental insights, Fourthstone holds ~100 conversations per quarter with bank management teams to discuss their strategy and expectations. "
        "They review management's target outcomes and how they plan to get there, in addition to updates on significant customers and industries the bank serves. "
        "Fourthstone may address areas of percieved weakness or risks to management's strategic plan. "
        "Technology investments are a growing part of these management discussions, as its role grows in the depositor relationship and in loan growth efforts. "
        "Failure to properly invest in technology can crimp loan growth efforts or erode deposit stickiness as customer experience stagnates. " \
        "In addition to management meetings, Fourthstone tracks regional economic developments via social media, local business journals, and real estate listings to gather earlier "
        "information on commerical loan activity within a given bank's service area. " \
        "Drilling down on loan book diversification among borrower type and terms illustrates different banks' varying sensitivities to duration and macroeconomic developments.  "
        "As a result, Fourthstone knows how regional lenders should benefit or suffer from a given economic or demographic tailwind, enabling them to take bets on other sectors " \
        "via regional bank equities.  "
        "<br/>""<br/>"

        "Extensive research on the commercial banking industry, individual loan books, and macroeconomic trends inform TBV estimates, " \
        "which identify mispricings in the market.  Fourthstone adds another dimension to their risk and return calculus by identifying " \
        "and anticipating key catalysts relevant to each position.  These catalysts, such as the "
        "interest rate environment, demographic trends, regulatory climate, or geopolitical landscape  "
        "could directly impact profit forecasts. " \
        "Some catalysts are better suited for trading opportunities than core portfolio positions—examples include index deletions and additions or coverage initiation by a sell side firm. " \
        "<br/>""<br/>"
        
        "Timing certain catalysts, especially credit or duration shocks, is difficult.  While predicting these catalysts is imprecise, identifying and tracking " \
        "market participants most sensitive to a potential catalyst is reliable, prudent preparation. " \
        "The lag between when catalysts occur and when their effects are seen in quarterly earnings "
        "is exacerbated by the lack of instituional sell-side coverage.  This presents desirable trading opportunities when stress " \
        "and volatility rise—Fourthstone has already compiled the relevant research and sensitivity analysis for the catalyst causing the unrest. " \
        "<br/>""<br/>"

        "Ideally, these volatility-inducing catalysts drive the portfolio's short positions towards fair value as new opportunities to deploy capital arise. " \
        "Short positions are established when Fourthstone finds banks with expensive valuations, weak fundamentals, and exogenous headwinds. " \
        "Expensive valuations are expensive relative to Fourthstone's internal projections and assumptions on fair value. " \
        "Weak fundamentals is a broad term including undesirable loan book concentrations, poor deposit quality, weak management teams, questionable balance sheet management, and aggressive underwriting, " \
        "among other factors.  Exogenous headwinds could be demographic shifts away from certain geographies, impending regulatory changes, passive vehicle flows, spurious headlines, or changes in trade policy. " \
        "Excessive leverage will magnify the effects of these headwinds. " \
        "<br/>""<br/>"

        "Fourthstone's research process is designed to find profitable investment opportunities.  "
        "While they do participate in short-term trading opportunities, the long and short books are driving returns from year to year. " \
        "Investment theses for the long and short book are about fundamental value—how effectively do they lend out depositors' capital? " \
        "Effective commercial banks should generate a better return on their capital, grow TBV faster, and trade at a higher P/TBV multiple than their peers. " \
        "Fourthstone identifies banks trading at a P/TBV that is not reflective of their fair value and invests accordingly."
        "<br/>""<br/>"

    )

    story.append(Paragraph(market_opp2, body_style))
    story.append(Paragraph("Portfolio Construction", h2_style))
    port_construct = (
        "Fourthstone's portfolio is structured as a combination of three investment groups: core longs, core shorts, and an opportunstic trading book. "
        "Positions are considered part of the opportunistic trading book when they are held for 30 days or less. "
        "Most positions enter the portfolio at 25-50bps at cost, increasing in size as conviction increases over time. " \
        "The core long book consists of 40-50 holdings of at least 1% of NAV, with confident ideas allocated at 3-5% of the portfolio at cost. " \
        "The core short book consists of 10-20 core short positions with smaller position sizes than the long book. " \
        "The total portfolio typically consists of 30-60 core positions.  "
        "<br/>""<br/>"
        "Fourthstone's aggregate turnover rate varies depending on allocations to the short and opportunistic trading books, but they generally hold their core long positions for 1-4 years.  " \
        "While there is no pre-determined minimum holding period, Fourthstone seeks to be tax efficient when feasible. "
        "Fourthstone typically shorts individual equities as a source of potential alpha, but will short ETFs during periods of elevated volatility or uncertainty. " \
        "Market sentiment and investor positioning are key considerations for the opportunistic trading book. "
        "No positions are permitted to be more than 10% of portfolio NAV at cost.  " \
        "<br/>""<br/>"
        "Gross portfolio exposure is capped at 200%, and has averaged 126% since inception.  " 
        "Net exposure is variable, ranging from (5)% to 128% since inception.  "
        "Net exposure is informed by the opportunity set identified by the research team and their macroeconomic outlook for the sector. "
        "Of all the month-end observations reviewed, 30% of months (46/151) ended with a net exposure less than 80%. " \
        "50% of months (76/151) ended with a net exposure between 80-110%, and 19% of months (29/151) ended with net exposure over 110%."
        
        ""
        )
    story.append(Paragraph(port_construct, body_style))
    story.append(Paragraph("Trading, Liquidity, and Portfolio Risk", h2_style))
    trading_and_risk = (
        "The portfolio manager (Phil Stone) has sole day-to-day trading authority for Fourthstone's funds.  The senior trader (Patrick Kelley) serves as an execution trader and the firm's " \
        "junior trader fills in and supports as necessary. "
        "Fourthstone does not employ automatic stop-loss limits.  If a position declines significantly, that will typically trigger a comprehensive review " \
        "of the position and associated investment thesis to determine if the thesis remains intact.  Certain adverse developments, " \
        "such as a report of accounting irregularities, usually result in an immediate exit of any pertinent long positions. "
        "<br/>""<br/>"

        "Once an investment idea is identified for purchase or sale, the PM determines the initial size, target price, and maximum position size. Orders are "
        "entered either via the PM, traders, or are placed via a broker. Orders are then run through an order management system for compliance checks against various criterias. In determining where to route the trade, the "
        "trader tries to determine where to obtain the best execution. When trading large orders they consider stock volumes and market impact. They seek to minimize Fourthstone’s “footprint” by trading "
        "larger orders in manageable segments and look for suitable counter parties to help achieve best execution. Once the position becomes part of the portfolio it is monitored in real time."
        "<br/>""<br/>"

        "Liquidity is a critical factor for Fourthstone's strategy."
        "The manager, traders, and operations team monitor trading volumes every day. They also monitor overall portfolio liquidity as a percentage of average daily trading volume to understand "
        "the portfolio's liquidity profile. It is part of their strategy to leverage the price advantage associated with less liquid offers within their overall liquidity parameters."
        "They utilize a combination of proprietary and external risk management tools available through "
        "Factset, Enfusion, and their trading platform. These include real time profit and loss, margin requirements, gross/net exposures, concentrations, portfolio, Beta, etc. to monitor the book."
        "<br/>""<br/>"

        "The firm employs various internal risk controls, including constant portfolio monitoring by the manager, traders, and operations team as well as trading platform limitations and restrictions. " \
        "They do not use any external risk monitoring service. "
        "Phil Stone and Rob Anderson work closely to quantify and mitigate portfolio risks including liquidity, geographic concentrations, and exposures to individual macroeconomic trends. " \
        "Ultimately, Phil Stone has the final say on any portfolio changes. "
    )
    story.append(Paragraph(trading_and_risk, body_style))
    story.append(Paragraph("Operations and Compliance", h2_style))
    ops_and_compliance = (
        "Fourthstone mitigates operational risks by contracting with specialized third parties and implementing redundancies for mission-critical applications.  "
        "The firm has access to three execution systems and five trading platforms for execution purposes as well as two prime broker relationships for additional flexibility. "
        "The firm engaged IQ-EQ to provide live "
        "monitoring of personal accounts and corporate email. Align Communications conducts disaster recovery testing, overall IT monitoring, patch management and"
        "ongoing vulnerability scans. BW Cyber conducts cybersecurity audits with penetration testing and overall risk assessment."
    )
    story.append(Paragraph(ops_and_compliance, body_style))
    
        #"long, short, opportunistic, variable net eposure, gross exposure, position limits etc."
    story.append(Paragraph("Performance Analysis", h2_style))
    #Include post-tax return analysis based on trailing K-1's; suitable for taxable investors?
    strategy_text = (
        "Fourthstone's net returns are compelling.  "
        "On an annualized basis, the Opportunity Fund has earned net returns of 18.6% compared to 4.8% for the Nasdaq Bank Index from January 2014 through July 2026. " 
        "The Nasdaq bank index includes each of the 232 domestic bank stocks listed on the NASDAQ exchange.  This index includes both large, mid, and small cap bank equities. "
        "The appendix includes the KBW Bank index ('Bank Idx') and KBW Regional Bank index (Reg Bank Idx).  " \
        "Fourthstone has outperformed these indices as well; the KBW Bank index returned 9.7% and the KBW Regional Bank index returned 6.9% over the same period."
        "Unlike the broad-based Nasdaq index, the KBW indices split bank equities by size.  "
        "Bulge bracket and national regional banks constitute the KBW Bank index, while small-to-mid size regional and community banks constitute the regional index. " \
        "All three indices are weighted by market cap. " \
        "<br/>""<br/>"

        "For a taxable investor, Fourthstone's after-tax returns are less enticing than headline net returns. " \
        "Assuming an investor is subject to the highest income tax bracket, they should expect a tax bill for 30-40% of the fund's net returns in a given year. " \
        "This figure can vary from year to year based on market volatility. For example, broad equity declines late in 2022 resulted in realized gains in excess of total return. " \
        "On the contrary, years like 2024 can result in minimal tax liabilities when unrealized returns, qualified dividends, and long-term capital gains make up most of the fund's net return. "
        "Ironically, taxable investors were likely thrilled to outperform the benchmark bank index and S&amp;P 500 by over 26% in 2022 and "
        "disappointed to underperform the benchmark by 4.5% and S&amp;P 500 by 12.7% in 2024. "
        "While tax inefficiency may cause some investors to pause, Fourthstone's track record during market downturns makes a strong case for a through-the-cycle allocation. " \
        "<br/>""<br/>" 

        "From January 2014 to July 2026, there were two major drawdown periods for bank equities. " \
        "After peaking in 2018, the Nasdaq Bank index declined over 51%, forming a trough in March 2020 before recovering to the prior peak on February 2021. "
        "From June 2018 to March 2020, the Nasdaq Bank index declined 44%, compared to a 17.6% decline for the Fourthstone Opportunity Fund.  Their long book posted losses "
        "of 23% while their short book gained just under 13% over the same period. "
        "For the full drawdown-and-recovery period from June 2018 to February 2021, Fourthstone posted net returns of 22.3% compared to a decline of 1.9% for the Nasdaq Bank index. " \
        "After fiscal and monetary stimulus boosted asset valuations post-COVID, "
        "the Nasdaq Bank index experienced another drawdown from January 2022 through July 2026, reaching a trough in May 2023.  "
        "From January 2022 to May 2023, the Nasdaq Bank index declined 43.0%, compared to a 17.4% decline in Fourthstone's Opportunity Fund, buoyed by a resilient long book posting loses of 20.6% " \
        "and a short book earning 10.0% over the same 17-month period. "
        "From January 2022 through July 2026, the bank index returned 1.0%, only surpassing its 2022 high in July 2026. "
        "Fourthstone posted net returns of 71.4% over the same period, generating an annualized return of 12.5%. " \
        "<br/>""<br/>" 
        "Fourthstone's track record shows that they can outperform in up markets in addition to protecting capital during drawdowns. "
        "Since 2014, the bank index's best annual returns were in 2021 (39.7%), 2016 (35.0%), and 2019 (21.2%). "
        "The Opportunity Fund posted better net returns in 2021 (54.8%) and 2016 (44.2%), and kept pace in 2019 (19.4%).  " \
        "<br/>""<br/>" 
        "" 



    )
    story.append(Paragraph(strategy_text, body_style))
    story.append(PageBreak())
        # Widths must sum up to total drawable space: 612 (letter width) - 108 (margins) = 504
    
    story.append(Paragraph("Footnotes", h1_style))
    footnotes = (
        "<sup>1</sup>: For privacy reasons, information in the Staff Overview is intentionally identical to the publicly available information on Fourthstone's website. "
        "<br/>""<br/>" \
        "<sup>2</sup>: Legislation regulating bank ownership includes the Bank Holding Company Act, Change in Bank Control Act, Securities Exchange Act (Section 16), and SEC disclosure obligations."
        "<br/>""<br/>"
        "<sup>3</sup>: FFIEC Call Report: a quarterly filing detailing the bank's balance sheet, income statement, and extensive supplementary schedules covering loan concentrations, regulatory capital ratios," \
        "   non-performing and past due loans, off balance sheet activities, and insurance assessments."
        "<br/>""<br/>"
        "FR Y-9: While the FFIEC report tracks individual bank subsidiaries, the FR Y-9 tracks the performance, risk profile, and financial health of the parent bank holdng company on a quarterly basis." \
        "Note that you would be required to file this if you exceeded a 10% stake in a publicly bank stock."
        "<br/>""<br/>"
        "FR 2644: "
        "   Weekly Report of Selected Assets and Liabilities of Domestically Chartered Commercial Banks and U.S. Branches and Agencies of Foreign Banks is a high-frequency balance sheet report. "
        "   It is also known as the bank credit report.  The Federal Reserve aggregates results and releases a macro-level H.8 report on Wedensday evening.  Banks with less than 5B in assets can opt to report monthly."
        "<br/>""<br/>"
        "FR Y-14 A/Q/M" \
        "   Report assessing capital adequacy and supporting stress tests under the Dodd-Frank Act. A required filing for banks and bank holding companies with more than 100B in consolidated assets." \
        "   The annual report includes quantitative capital projections and is published as part of the Federal Reserve Stress Test Results Report" \
        "   The quarterly report includes asset classses, capital components, and PPNR.  "
        "       Federal Reserve uses these granular asset details internally to calibrate the macro-simulations and economic stress models that fuel the annual DFAST aggregate results." \
        "   The monthly report includes detailed loan portfolio collections (mortgage, credit cards), which are published to FRED.  Records for individual banks are confidential across each iteration of the report. "
        "<br/>""<br/>"
        "FDIC Quarterly Banking Profile, An aggregated quarterly report that tracks the ocerall health, performance, and risk profile of FDIC-insured institutions."
        "<br/>""<br/>"
        "Uniform Bank Performance Report: A tool provided by FFIEC that aggregates and standardizes FFIEC Call Report data across customizable peer bank groups for easier comparative analysis." 


    )
    story.append(Paragraph(footnotes, body_style))

    story.append(NextPageTemplate('Landscape'))
    story.append(PageBreak())
    perf_table = get_tearsheet_data()
    print("\nTearsheet Data")
    print(perf_table)

    up_table, down_table = get_updown_data()
    print("\nUp Data")
    print(up_table)    
    print("\nDown Data")
    print(down_table)

    appendix_width = landscape_size[0] - 108
    appendix_sections = [
        ("Appendix A: Full-Period Performance", perf_table),
        ("Appendix B: Up-Market Performance", up_table),
        ("Appendix C: Down-Market Performance", down_table),
    ]
    for section_index, (section_title, section_data) in enumerate(appendix_sections):
        story.append(Paragraph(section_title, appendix_title_style))
        story.append(build_appendix_table(
            section_data,
            appendix_header_style,
            appendix_metric_style,
            appendix_cell_style,
            appendix_width
        ))
        if section_index < len(appendix_sections) - 1:
            story.append(PageBreak())

    metric_definitions = [
        ["Metric", "Definition"],
        [
            "Total Months",
            "Number of monthly observations remaining after aligning portfolio and benchmark returns and removing missing values.",
            #"N = count(r_t)"
        ],
        [
            "First Month End",
            "Earliest month-end date in the aligned return series.",
            #"min(date_t)"
        ],
        [
            "Last Month End",
            "Latest month-end date in the aligned return series.",
            #"max(date_t)"
        ],
        [
            "Up Months",
            "Number of months in which the applicable return series is strictly positive.",
            #"Count(r_t > 0)"
        ],
        [
            "Down Months",
            "Number of months in which the applicable return series is zero or negative.",
            #"Count(r_t <= 0)"
        ],
        [
            "Cumulative Return",
            "Total compounded return over the full measurement period.",
            #"R_cum = Product[t=1..N](1 + r_t) - 1"
        ],
        [
            "Annualized Return (CAGR)",
            "Geometric annualized return derived from cumulative return and the number of monthly observations.",
            #"CAGR = (1 + R_cum)^(12 / N) - 1"
        ],
        [
            "Annualized Volatility",
            "Sample standard deviation of monthly returns, scaled to an annual frequency.",
            #"Vol_ann = StdDev(r_t) * sqrt(12)"
        ],
        [
            "Sharpe Ratio",
            "Annualized excess return per unit of total return volatility. The annual risk-free rate is converted to a monthly rate.",
            #"Sharpe = Mean(r_t - r_f / 12) / StdDev(r_t) * sqrt(12)"
        ],
        [
            "Sortino Ratio",
            "Annualized excess return divided by the sample standard deviation of negative monthly returns.",
            #"Sortino = Mean(r_t - r_f / 12) / StdDev({r_t | r_t < 0}) * sqrt(12)"
        ],
        [
            "Max Drawdown",
            "Largest peak-to-trough decline in compounded portfolio wealth.",
            #"W_t = Product[i=1..t](1 + r_i); P_t = max[i<=t](W_i); MDD = min_t(W_t / P_t - 1)"
        ],
        [
            "Calmar Ratio",
            "Annualized return per unit of absolute maximum drawdown.",
            #"Calmar = CAGR / abs(MDD)"
        ],
        [
            "Alpha (Annualized)",
            "Annualized return above the return implied by the risk-free rate and portfolio beta versus the benchmark.",
            #"Alpha = CAGR_p - [r_f + Beta * (CAGR_b - r_f)]"
        ],
        [
            "Beta vs Benchmark",
            "Sensitivity of portfolio monthly returns to benchmark monthly returns.",
            #"Beta = Cov(r_p,t, r_b,t) / Var(r_b,t)"
        ],
        [
            "Treynor Ratio",
            "Annualized excess return per unit of benchmark beta.",
            #"Treynor = (CAGR_p - r_f) / Beta"
        ],
        [
            "Tracking Error (Ann.)",
            "Annualized sample standard deviation of monthly active returns.",
            #"TE = StdDev(r_p,t - r_b,t) * sqrt(12)"
        ],
        [
            "Information Ratio",
            "Annualized arithmetic active return divided by annualized tracking error.",
            #"IR = Mean(r_p,t - r_b,t) * 12 / TE"
        ],
        [
            "Monthly VaR (90% Conf.)",
            "Historical one-month loss threshold based on the 10th percentile of observed monthly returns.",
            #"VaR_90 = -Percentile(r_t, 10)"
        ],
        [
            "Monthly VaR (99% Conf.)",
            "Historical one-month loss threshold based on the 1st percentile of observed monthly returns.",
            #"VaR_99 = -Percentile(r_t, 1)"
        ],
    ]

    story.append(PageBreak())
    story.append(Paragraph(
        "Appendix D: Performance Metric Definitions",
        appendix_title_style
    ))
    story.append(build_metric_definitions_table(
        metric_definitions,
        appendix_header_style,
        appendix_metric_style,
        appendix_definition_style,
        appendix_width
    ))

    
    # Construct PDF using custom dual-pass NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)

if __name__ == "__main__":
    create_hedge_fund_report("hedge_fund_research_report.pdf")
    print("Report compiled successfully as 'hedge_fund_research_report.pdf'.")

"""
    comp_edge = (
        
        "Their flexibility to go long/short and adjust their portfolio's net exposure allows them to take positions on almost any high-conviction thesis within their coverage area. "
        "This incentivizes the team to continually update their outlook on the sector and individual banks in case prices suddenly deviate from Fourthstone's fair value estimates. " \
        "To develop high-conviction theses, Fourthstone performs exhaustive research on the commercial banking industry and its component companies, as well as the companies these banks lend to. "
        "Their sector focus results in a high return on research " \
        "as each research note may inform opinions on the entire portfolio.  Quantitative regulatory data is considered along with qualitative, fundamental insights into profit forecasts and potential catalysts. " \
        "<br/>""<br/>"
        "Fourthstone aggregates and synthesizes data from banks' requisite regulatory filings as it is released. This data shows balance sheet trends for the industry and individual banks. " \
        "You can see X, Y, Z in these releases. "
        "Tracking loan books over time shows how different sectors of the economy are performing and which banks are participating.  " \
        "By maintaining an updated knowledge base of individual banks and relevant economic trends, Fourthstone positions itself to implement investment theses quickly in response to market movements. "
        "Implementation speed is a point of emphasis for their team as they seek to capitalize on the informational advantages they develop before this edge decays and P/TBV valuations adjust. "
        "<br/>""<br/>"

        "Quantitative balance sheet data is complemented by a layer of qualitative analysis to project TBV growth and derive fair value estimates. "
        "Effective fundamental research provides context to expectations of loan growth—"
        "diversification, underwriting discipline, or rational pricing may be diminished when bank management pursues other goals. " \
        "They seek every incremental insight into the banks' deposit quality, underwriting culture, loan growth expectations, loan book diversification, "
        "balance sheet positioning, technology investment, anything that may affect future TBV.  "
        "In pursuit of these incremental insights, Fourthstone holds ~100 conversations per quarter with bank management teams to discuss their strategy and expectations. " \
        "Technology investments are a growing part of these management discussions, as its role grows in the depositor relationship and in loan growth efforts. "
        "Failure to properly invest in technology can crimp loan growth efforts or erode deposit stickiness as customer experience stagnates. " \
        "Fourthstone tracks regional economic developments via social media, local business journals, and real estate listings to gather earlier information on commerical loan activity within a given bank's service area. " \
        "Drilling down on loan book diversification among borrower type and terms illustrate how different banks have varying sensitivities to duration and macroeconomic developments.  "
        "As a result, Fourthstone knows how regional lenders should benefit or suffer from a given economic or demographic tailwind, enabling them to take bets on other sectors " \
        "via regional bank equities.  "
        "<br/>""<br/>"
        
        "Extensive research on the commercial banking industry, individual loan books, and macroeconomic trends inform TBV estimates, " \
        "which identify mispricings in the market.  Fourthstone adds another dimension to their risk and return calculus by identifying " \
        "and anticipating key catalysts relevant to each position.  These catalysts, such as the "
        "interest rate environment, demographic trends, regulatory climate, or geopolitical landscape  "
        "could directly impact profit forecasts. " \
        "Some catalysts are better suited for trading opportunities than core portfolio positions—examples include index deletions and additions or coverage initiation by a sell side firm. " \
        "<br/>""<br/>"
        
        "Timing certain catalysts, especially credit or duration shocks, is difficult.  While predicting these catalysts is imprecise, identifying and tracking " \
        "market participants most sensitive to a potential catalyst is prudent preparation. " \
        "The lag between when catalysts occur and when their effects are seen in quarterly earnings "
        "is exacerbated by the lack of instituional sell-side coverage.  This presents desirable trading opportunities when stress " \
        "and volatility rise—Fourthstone has already compiled the relevant research and sensitivity analysis for the catalyst causing the unrest. " \
        "<br/>""<br/>"

        "Ideally, these volatility-inducing catalysts drive the portfolio's short positions towards fair value as new opportunities to deploy capital arise. " \
        "Short positions are established when Fourthstone finds banks with expensive valuations, weak fundamentals, and exogenous headwinds. " \
        "Expensive valuations are expensive relative to Fourthstone's internal projections and assumptions on fair value. " \
        "Weak fundamentals is a broad category including undesirable loan book concentrations, poor deposit quality, weak management teams, questionable balance sheet management, and aggressive underwriting, " \
        "among other factors.  Exogenous headwinds could be demogrpahic shifts away from certain locales, impending regulatory changes, passive vehicle flows, spurious headlines, or changes in trade policy. " \
        "Excessive leverage will magnify the effects of these headwinds. " \
        "<br/>""<br/>"

        "Fourthstone's research process is designed to find profitable investment opportunities.  "
        "While they do participate in short-term trading opportunities, the long and short books are driving returns from year to year. " \
        "Investment theses for the long and short book are about fundamental value—how effectively to they lend out depositors capital? " \
        "Effective commercial banks should generate a better return on their capital, grow TBV faster, and trade at a higher P/TBV multiple than their peers. " \
        "Fourthstone identifies banks trading at a P/TBV that is not reflective of their fundamental value and invests accordingly."
        "<br/>""<br/>"

        )
        "Fundamental analysis only gets you part of the way to high-conviction theses.  Not trading at fair value?  What are the catalysts that will get you there?" \
        "The key to generating profitable ideas is the qualitative insight layered on top of Fourthstone's quantitative systems.  "
        " to better project future tangible book value and income growth" \
        "They seek every available incremental insight into the banks' deposit quality, underwriting culture, and loan growth projections.  Examples include  "
        "having ~100 conversations per quarter with bank management teams and tracking local business journals and magazines for commerical loan activity within a given bank's service area. "
        "By developing a perspective on the fundamental value and potential catalysts for individual banks, Fourthstone can confidently gauge the " \
        "Industrywide filings, as well as their aggregate internal research on individual bank equities, help to inform Fourthstone's economic outlook for the domestic commerical banking industry. " \
        "A confident industry outlook can drive a quick change in their net exposure, which has ranged from slightly negative to 130%, but spends roughly half the time (76/151 months observed) between 80-110%.  " \
        ""

        "The the portfolio's net exposure is determined by the combined evidence of their macroeconomic outlook and fair value estimtates in relation to current prices. " \
        " " \
        "" \
        ""
        "Generally, they look for at least a 20% margin of safety between fair value and current price for both longs and shorts in the portfolio. " \
        "Their variable net exposure is a function of the long and short opportunities that they see in the market. " \
        ""
        "As a result, their fair value estimates determine individual positions and total exposure for the portfolio. " \
        "" \
        ""
        ""
    "Fourthstone's exhaustive research on fundamentals, macro trends, and loan book exposures identifies growing banks with upside catalysts "
    "as well as short sale opportunities possessing undesirable loan book concentrations, questionable underwriting, poor deposit quality, weak management teams, or unfavorable balance sheet positioning. "

    "Fourthstone typically uses price to tangible book value (P/TBV) to identify and compare commercial bank valuations, seeking a fair value margin of at least 20% on any given portfolio position. "
            ""
        "Then performance analysis; how does the fund perform as liquidity exits the financial system?" \
        "measurements of liquidity?:"           
        "Credit analysis is at the core of investment strategy.  Regardless of market valuation or geopolitical concerns, regional lenders will still lend. <br/>" \
        "Intense research process focused on making quick decisions; Opposite of Tiger Global --> Tiger Cub pipeline"
        "Portfolio risk and position sizing is managed by Rob and Phil, with Phil having the ultimate say on portfolio changes"
        "Quantitative bank data readily available, qualitative data is more mundane to gather and process but essential to determing details. mLocal biz journals and bulletins a great resource." \
        "Transparent businesses, 0 industry risk" \
        "How do they generate alpha?  What is the core strategy?"
        "What is their investment universe? Size/#companies/liquidity/geography/marketcaps?  Any key advantages or constraints?"
        "Walk through idea generation to portfolio implementation --> speed? thorough process? Research/trading alpha?"
        "Portfolio construction and attributes--number of positions, gross and net exposure trends/limits, leverage usage and type, liquidity of underlying assets"

        "Often, loan growth may come at the relative sacrifice of underwriting discipline or loan book diversification. "
                "Correlation to liquidity measures" \
        "" \
        "Risk/Return scatterplot, 3d plot with max drawdown." \
        "Gross exposures stacked on sideways t chart with net exposure line graph with scale on rhs, high contrast." \
        "" \
        "Closing Argument; restate support behind recommendation from 30kft view." \
        "<br/>""<br/>"
        "<br/>""<br/>"
        "Closing line/para." 
"""