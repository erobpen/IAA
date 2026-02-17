from flask import Flask, render_template
import base64
from analyzer import analyze_strategy
import inflation

import dividend_module
import lda
import small_cap

app = Flask(__name__)

@app.route('/')
def dashboard():
    # Strategy Analysis
    img, table_data = analyze_strategy()
    plot_url = base64.b64encode(img.getvalue()).decode()
    
    # Inflation Analysis
    inf_img, inf_table = inflation.analyze_inflation()
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
    sc_img, sc_table = small_cap.analyze_small_cap()
    if sc_img:
        sc_plot_url = base64.b64encode(sc_img.read()).decode()
    else:
        sc_plot_url = None

    return render_template('dashboard.html', 
                           plot_url=plot_url, 
                           table_data=table_data,
                           inf_plot_url=inf_plot_url,
                           inf_table=inf_table,

                           div_plot_url=div_plot_url,
                           div_table=div_table,
                           lda_plot_url=lda_plot_url,
                           lda_table=lda_table,
                           sc_plot_url=sc_plot_url,
                           sc_table=sc_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
