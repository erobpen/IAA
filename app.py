from flask import Flask, render_template, request, jsonify
import base64
from analyzer import analyze_strategy, analyze_strategy_filtered
import inflation

import dividend_module
import lda
import small_cap
import lsc
import lscda
import interest_rate
import margin
import database
import data_cache

app = Flask(__name__)

# Initialize database once at startup
database.init_db()


def _encode_image(img):
    """Encode a BytesIO image to base64 string, handling both .getvalue() and .read()."""
    if img is None:
        return None
    return base64.b64encode(img.getvalue()).decode()


@app.route('/')
def dashboard():
    # Clear cache at start of each request so all tabs share fresh data
    data_cache.clear()

    # Strategy Analysis
    img, table_data = analyze_strategy()
    plot_url = _encode_image(img)
    
    # LSC Analysis
    lsc_img, lsc_table = lsc.analyze_lsc()
    lsc_plot_url = _encode_image(lsc_img)

    # LSCDA Analysis
    lscda_img, lscda_table = lscda.analyze_lscda()
    lscda_plot_url = _encode_image(lscda_img)
        
    # Interest Rate Analysis
    ir_img, ir_table = interest_rate.analyze_interest_rate()
    ir_plot_url = _encode_image(ir_img)
    
    # Inflation Analysis
    inf_img, inf_table, inf_cagr, inf_cagr_1942 = inflation.analyze_inflation()
    inf_plot_url = _encode_image(inf_img)

    # Dividend Analysis
    div_img, div_table = dividend_module.analyze_dividend()
    div_plot_url = _encode_image(div_img)

    # LDA Analysis
    lda_img, lda_table = lda.analyze_lda()
    lda_plot_url = _encode_image(lda_img)
        
    # Small Cap Analysis
    sc_img, sc_table, sc_cagr = small_cap.analyze_small_cap()
    sc_plot_url = _encode_image(sc_img)

    # Margin Analysis
    margin_img, margin_table = margin.analyze_margin()
    margin_plot_url = _encode_image(margin_img)

    return render_template('dashboard.html', 
                           plot_url=plot_url, 
                           table_data=table_data,
                           lsc_plot_url=lsc_plot_url,
                           lsc_table=lsc_table,
                           lscda_plot_url=lscda_plot_url,
                           lscda_table=lscda_table,
                           ir_plot_url=ir_plot_url,
                           ir_table=ir_table,
                           inf_plot_url=inf_plot_url,
                           inf_table=inf_table,
                           inf_cagr=inf_cagr,
                           inf_cagr_1942=inf_cagr_1942,
                           margin_plot_url=margin_plot_url,
                           margin_table=margin_table,

                           div_plot_url=div_plot_url,
                           div_table=div_table,
                           lda_plot_url=lda_plot_url,
                           lda_table=lda_table,
                           sc_plot_url=sc_plot_url,
                           sc_table=sc_table,
                           sc_cagr=sc_cagr)

@app.route('/api/inflation_cagr')
def get_inflation_cagr():
    try:
        start_year = int(request.args.get('start'))
        end_year = int(request.args.get('end'))
        
        cagr = inflation.calculate_period_cagr(start_year, end_year)
        
        if cagr is not None:
             return jsonify({'cagr': f"{cagr:.2f}%", 'error': None})
        else:
             return jsonify({'cagr': None, 'error': 'Invalid Range or No Data'})
             
    except Exception as e:
        return jsonify({'cagr': None, 'error': str(e)})

@app.route('/api/small_cap_cagr')
def get_small_cap_cagr():
    try:
        start_year = int(request.args.get('start'))
        end_year = int(request.args.get('end'))
        
        cagr = small_cap.calculate_period_cagr(start_year, end_year)
        
        if cagr is not None:
             return jsonify({'cagr': f"{cagr:.2f}%", 'error': None})
        else:
             return jsonify({'cagr': None, 'error': 'Invalid Range or No Data'})
             
    except Exception as e:
        return jsonify({'cagr': None, 'error': str(e)})

@app.route('/api/leverage/filter')
def get_leverage_filtered():
    try:
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        
        img = analyze_strategy_filtered(start, end)
        
        if img is not None:
            plot_b64 = base64.b64encode(img.getvalue()).decode()
            return jsonify({'plot': plot_b64, 'error': None})
        else:
            return jsonify({'plot': None, 'error': 'No data for the selected range'})
    except Exception as e:
        return jsonify({'plot': None, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
