from flask import Flask, render_template
import base64
from analyzer import analyze_strategy

app = Flask(__name__)

@app.route('/')
def dashboard():
    img, table_data = analyze_strategy()
    plot_url = base64.b64encode(img.getvalue()).decode()
    return render_template('dashboard.html', plot_url=plot_url, table_data=table_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
