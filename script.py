"""
File: script.py
Description: Logic for the Consultative Sales Script with Social Proof & Value Stacking.
"""

def get_state(step_id):
    """
    Returns the content for the current step.
    """
    script_data = {
        0: {
            "text": "Hi Sarah! 👋 As a business owner, I know you wear a lot of hats. To help me recommend the right tools, what's taking up the biggest chunk of your administrative time lately?",
            "options": [
                {"label": "Managing client contracts", "next": 1},
                {"label": "Organizing project files", "next": 2}
            ]
        },
        1: {
            # QUALIFY: Digging into the specific workflow
            "text": "Contracts are definitely time-consuming. 📄 \n\nWhen you send a proposal to a client, how are you currently getting them to sign it?",
            "options": [
                {"label": "I pay for DocuSign", "next": 3},
                {"label": "I print, sign, and scan", "next": 3}
            ]
        },
        2: {
            # QUALIFY: Alternative path
            "text": "Keeping files organized is key. I often see creative agencies struggle with version control on legal documents.\n\nHow do you currently handle client sign-offs?",
            "options": [
                {"label": "External eSign tools", "next": 3},
                {"label": "Email threads & scans", "next": 3}
            ]
        },
        3: {
            # AGITATE + SOCIAL PROOF
            "text": "I hear that often. In fact, many **agencies similar to yours** have switched to Google eSignature recently to eliminate that 'tab-switching fatigue'. \n\nConsolidating your tools saves time and prevents version errors. Did you know you can request signatures directly inside this Doc?",
            "options": [
                {"label": "Really? How?", "next": 4},
                {"label": "Is it secure?", "next": 5}
            ]
        },
        4: {
            # SOLUTION: Selling Points (Integrated, Easy)
            "text": "It's seamless. You just drag a signature field onto the page, email it to the client, and they sign it instantly—**no Google account required for them**. \n\nIt stays integrated in Drive, so you never lose a contract again.",
            "options": [
                {"label": "How much is it?", "next": 6},
                {"label": "I'm not ready to switch.", "next": 7}
            ]
        },
        5: {
            # OBJECTION: Security
            "text": "Absolutely. Google eSignature complies with the same industry standards as major providers (like eIDAS). It automatically generates a secure audit trail for every contract.",
            "options": [
                {"label": "Sounds good. Pricing?", "next": 6}
            ]
        },
        6: {
            # VALUE STACK: Sweetening the Deal (Gemini, Storage, etc.)
            "text": "The Business Standard plan is **$12/user/month**. \n\nThat includes eSignature, but you also get **Gemini AI** to help write proposals, **Appointment Booking** pages for clients, and **2TB** of secure storage.",
            "options": [
                {"label": "Okay, upgrade me.", "next": 8},
                {"label": "It's a bit over budget.", "next": 7}
            ]
        },
        7: {
            # THE "HAIL MARY": Discount or Trial
            "text": "I understand. Budget is tight for growing agencies.\n\nI really want you to experience the productivity boost. I can offer you a **20% discount** on the annual plan, OR a **30-day Free Trial** to test it out.",
            "options": [
                {"label": "I'll take the 20% discount!", "next": 8},
                {"label": "Start 30-Day Free Trial", "next": 9},
                {"label": "No thanks, I'll pass.", "next": 99}
            ]
        },
        8: {
            # SUCCESS: Upgrade
            "text": "🎉 Upgrade Initiated! \n\nWe've applied the discount. Please refresh this tab. You will see the **eSignature** option appear in your 'Insert' menu within 30 seconds.",
            "options": [] # End
        },
        9: {
            # SUCCESS: Trial
            "text": "✅ Your 30-Day Free Trial is active! \n\nYou can use eSignatures immediately. We won't charge you until the trial ends, and you can cancel anytime.",
            "options": [] # End
        },
        99: {
            # EXIT: Walk Away
            "text": "No problem at all! The offer will remain in your Admin Console if you decide to streamline your contracts later. \n\nHave a productive day, Sarah!",
            "options": [] # End
        }
    }

    return script_data.get(step_id)