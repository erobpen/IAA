from flask import Flask, render_template
import base64
from analyzer import analyze_strategy
import inflation
import lia

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
        
    # LIA Analysis
    lia_img, lia_table = lia.analyze_lia()
    if lia_img:
        lia_plot_url = base64.b64encode(lia_img.getvalue()).decode()
    else:
        lia_plot_url = None
        
    return render_template('dashboard.html', 
                           plot_url=plot_url, 
                           table_data=table_data,
                           inf_plot_url=inf_plot_url,
                           inf_table=inf_table,
                           lia_plot_url=lia_plot_url,
                           lia_table=lia_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
