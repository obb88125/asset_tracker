from flask import jsonify
from routes import dashboard_bp
from services.statistics import get_summary_stats, get_monthly_flow, get_people_share, get_cumulative_flow, get_heatmap_data, get_account_comparison

@dashboard_bp.route('/summary', methods=['GET'])
def summary():
    try:
        data = get_summary_stats()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@dashboard_bp.route('/monthly', methods=['GET'])
def monthly():
    try:
        data = get_monthly_flow()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@dashboard_bp.route('/people-share', methods=['GET'])
def people_share():
    try:
        data = get_people_share()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@dashboard_bp.route('/cumulative', methods=['GET'])
def cumulative():
    try:
        data = get_cumulative_flow()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@dashboard_bp.route('/heatmap', methods=['GET'])
def heatmap():
    try:
        data = get_heatmap_data()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@dashboard_bp.route('/account-comparison', methods=['GET'])
def account_comparison():
    try:
        data = get_account_comparison()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
