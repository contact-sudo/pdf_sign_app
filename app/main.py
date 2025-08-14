from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import os, base64, shutil, yaml
from pdf_overlay import burn_fields_and_signature

KV = """
<RootUI@TabbedPanel>:
    do_default_tab: False
    TabbedPanelItem:
        text: "Sample PDFs"
        BoxLayout:
            orientation: 'vertical'; padding: dp(10); spacing: dp(8)
            BoxLayout:
                size_hint_y: None; height: dp(40); spacing: dp(8)
                Label: text: "Stored in: " + app.samples_dir; text_size: self.size; halign: 'left'; valign: 'middle'
                Button: text: "Add PDF"; size_hint_x: None; width: dp(120); on_release: app.open_file_picker()
            BoxLayout: size_hint_y: None; height: dp(36)
                Label: text: "Available PDFs:"; bold: True
            BoxLayout: id: samples_list; orientation: 'vertical'; size_hint_y: 1
    TabbedPanelItem:
        text: "Fill & Sign"
        BoxLayout:
            orientation: 'vertical'; padding: dp(10); spacing: dp(8)
            BoxLayout:
                size_hint_y: None; height: dp(40); spacing: dp(8)
                Label: text: "Choose sample PDF"; size_hint_x: None; width: dp(150)
                Spinner:
                    id: sample_spinner; text: app.selected_pdf if app.selected_pdf else "Select..."
                    values: app.sample_files; on_text: app.on_select_pdf(self.text)
            GridLayout:
                cols: 2; size_hint_y: None; height: self.minimum_height
                row_default_height: dp(48); row_force_default: True; spacing: dp(6); padding: dp(4)
                Label: text: "Name"
                TextInput: id: name_input; multiline: False; hint_text: "Enter full name"
                Label: text: "Date of Birth (YYYY-MM-DD)"
                TextInput: id: dob_input; multiline: False; hint_text: "e.g., 1990-05-21"
            BoxLayout:
                orientation: 'vertical'; size_hint_y: None; height: dp(220)
                Label: text: "Signature (draw below)"; size_hint_y: None; height: dp(24)
                SignaturePad: id: sigpad; size_hint_y: None; height: dp(160)
                BoxLayout: size_hint_y: None; height: dp(36); spacing: dp(8)
                    Button: text: "Clear"; on_release: app.clear_signature()
            Button: text: "Create Signed PDF"; size_hint_y: None; height: dp(48); on_release: app.create_signed_pdf()
<SignaturePad@Widget>:
    canvas.before:
        Color: rgba: 0.95,0.95,1,1
        Rectangle: pos: self.pos; size: self.size
    on_touch_down: app.sig_touch_down(*args)
    on_touch_move: app.sig_touch_move(*args)
"""

class PDFApp(App):
    title = "PDF Fill & Sign (APK)"
    samples_dir = StringProperty("samples"); out_dir = StringProperty("out")
    sample_files = ListProperty([]); selected_pdf = StringProperty("")
    def build(self):
        Builder.load_string(KV); self.root = Builder.template("RootUI")
        base = os.path.dirname(os.path.abspath(__file__))
        self.samples_dir = os.path.join(base, "samples"); self.out_dir = os.path.join(base, "out")
        os.makedirs(self.samples_dir, exist_ok=True); os.makedirs(self.out_dir, exist_ok=True)
        self.refresh_samples_list(); return self.root
    def alert(self, title, msg): Popup(title=title, content=Label(text=msg), size_hint=(0.9,0.4)).open()
    def refresh_samples_list(self):
        files = sorted([f for f in os.listdir(self.samples_dir) if f.lower().endswith(".pdf")])
        self.sample_files = files; c = self.root.ids.samples_list; c.clear_widgets()
        if not files: c.add_widget(Label(text="(No PDFs yet)", size_hint_y=None, height=dp(30))); return
        for f in files:
            row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
            row.add_widget(Label(text=f, halign='left', valign='middle'))
            btn = Button(text="Delete", size_hint_x=None, width=dp(90))
            def make_del(n): return lambda *_: self.delete_sample(n)
            btn.bind(on_release=make_del(f)); row.add_widget(btn); c.add_widget(row)
    def delete_sample(self, name):
        try: os.remove(os.path.join(self.samples_dir, name))
        except Exception as e: self.alert("Delete error", str(e))
        self.refresh_samples_list()
    def open_file_picker(self):
        chooser = FileChooserIconView(filters=['*.pdf'], path=os.path.expanduser("~"))
        popup = Popup(title="Select a PDF to import", content=chooser, size_hint=(0.95,0.9))
        def on_submit(_, selection):
            if selection:
                src = selection[0]
                try: 
                    dest = os.path.join(self.samples_dir, os.path.basename(src))
                    shutil.copy2(src, dest); self.refresh_samples_list()
                except Exception as e: self.alert("Import error", str(e))
            popup.dismiss()
        chooser.bind(on_submit=on_submit); popup.open()
    def on_select_pdf(self, text):
        if text in self.sample_files: self.selected_pdf = text
    def sig_touch_down(self, widget, touch):
        if not widget.collide_point(*touch.pos): return False
        from kivy.graphics import Color, Line
        with widget.canvas: Color(0,0,0,1); touch.ud['line'] = Line(points=(touch.x, touch.y), width=2)
        return True
    def sig_touch_move(self, widget, touch):
        from kivy.graphics import Line
        if 'line' in touch.ud: touch.ud['line'].points += (touch.x, touch.y)
    def clear_signature(self):
        pad = self.root.ids.sigpad; pad.canvas.clear()
        from kivy.graphics import Color, Rectangle
        with pad.canvas.before: Color(0.95,0.95,1,1); Rectangle(pos=pad.pos, size=pad.size)
    def _signature_png(self):
        pad = self.root.ids.sigpad
        from kivy.graphics import Fbo, ClearColor, ClearBuffers; from PIL import Image; import io as _io
        fbo = Fbo(size=pad.size, with_stencilbuffer=True); fbo.add(ClearColor(1,1,1,1)); fbo.add(ClearBuffers()); fbo.add(pad.canvas); fbo.draw()
        data = fbo.texture.pixels; img = Image.frombytes('RGBA', (int(pad.width), int(pad.height)), data); b=_io.BytesIO(); img.save(b, format="PNG"); return b.getvalue()
    def create_signed_pdf(self):
        name = self.root.ids.name_input.text.strip(); dob = self.root.ids.dob_input.text.strip()
        if not self.selected_pdf: self.alert("Missing PDF","Please choose a sample PDF."); return
        if not name or not dob: self.alert("Missing info","Enter both Name and DOB (YYYY-MM-DD)."); return
        try: dob_token = datetime.strptime(dob, "%Y-%m-%d").strftime("%Y%m%d")
        except Exception: self.alert("Invalid DOB","Use YYYY-MM-DD, e.g., 1990-05-21"); return
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"fields.yaml")
        if os.path.exists(cfg_path): fields_cfg = yaml.safe_load(open(cfg_path,"r",encoding="utf-8"))
        else:
            fields_cfg={"fields":[{"name":"ApplicantName","type":"text","page":0,"x":120,"y":520,"font_size":12},
                                  {"name":"DOB","type":"text","page":0,"x":120,"y":500,"font_size":12},
                                  {"name":"Signature","type":"signature","page":0,"x":120,"y":440,"w":220,"h":60}]}
        base_pdf_path = os.path.join(self.samples_dir, self.selected_pdf)
        try: base_pdf = open(base_pdf_path,"rb").read()
        except Exception as e: self.alert("Read error", str(e)); return
        values = {"ApplicantName": name, "DOB": dob, "Name": name, "DateOfBirth": dob}
        import base64; sig_data_url = "data:image/png;base64," + base64.b64encode(self._signature_png()).decode("utf-8")
        try: out_bytes = burn_fields_and_signature(base_pdf, fields_cfg, values, sig_data_url)
        except Exception as e: self.alert("PDF error", str(e)); return
        out_name = f"{name.replace(' ', '_')}_{dob_token}.pdf"; out_path = os.path.join(self.out_dir, out_name)
        try: open(out_path,"wb").write(out_bytes)
        except Exception as e: self.alert("Save error", str(e)); return
        self.alert("Saved", f"Saved to: {out_path}\nOpen with a file manager or share it."); self.clear_signature()
def run_desktop():
    if platform != "android": Window.size = (1000,700)
    PDFApp().run()
if __name__ == "__main__": run_desktop()
