from flask import Flask, render_template
import base64
from analyzer import analyze_strategy
import inflation

import dividend_module
import lda
import small_cap
import lsc
import lscda

app = Flask(__name__)

@app.route('/')
def dashboard():
    # Strategy Analysis
    img, table_data = analyze_strategy()
    plot_url = base64.b64encode(img.getvalue()).decode()
    
    # LSC Analysis
    lsc_img, lsc_table = lsc.analyze_lsc()
    if lsc_img:
        lsc_plot_url = base64.b64encode(lsc_img.getvalue()).decode()
    else:
        lsc_plot_url = None

    # LSCDA Analysis
    lscda_img, lscda_table = lscda.analyze_lscda()
    if lscda_img:
        lscda_plot_url = base64.b64encode(lscda_img.getvalue()).decode()
    else:
        lscda_plot_url = None
    
    # Inflation Analysis
    inf_img, inf_table, inf_cagr, inf_cagr_1942 = inflation.analyze_inflation()
    if inf_img:
        inf_plot_url = base64.b64encode(inf_img.getvalue()).decode()
    else:
        inf_plot_url = None
        


    # Dividend Analysis
    div_img, div_table = dividend_module.analyze_dividend()
    if div_img:
        div_plot_url = base64.b64encode(div_img.read()).decode()
    else:
        div_plot_url = None

    # LDA Analysis
    lda_img, lda_table = lda.analyze_lda()
    if lda_img:
        lda_plot_url = base64.b64encode(lda_img.read()).decode()
    else:
        lda_plot_url = None
        
    # Small Cap Analysis
    sc_img, sc_table, sc_cagr = small_cap.analyze_small_cap()
    if sc_img:
        sc_plot_url = base64.b64encode(sc_img.read()).decode()
    else:
        sc_plot_url = None

    return render_template('dashboard.html', 
                           plot_url=plot_url, 
                           table_data=table_data,
                           lsc_plot_url=lsc_plot_url,
                           lsc_table=lsc_table,
                           lscda_plot_url=lscda_plot_url,
                           lscda_table=lscda_table,
                           inf_plot_url=inf_plot_url,
                           inf_table=inf_table,
                           inf_cagr=inf_cagr,
                           inf_cagr_1942=inf_cagr_1942,

                           div_plot_url=div_plot_url,
                           div_table=div_table,
                           lda_plot_url=lda_plot_url,
                           lda_table=lda_table,
                           sc_plot_url=sc_plot_url,
                           sc_table=sc_table,
                           sc_cagr=sc_cagr)

@app.route('/api/inflation_cagr')
def get_inflation_cagr():
    from flask import request, jsonify
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
    from flask import request, jsonify
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
