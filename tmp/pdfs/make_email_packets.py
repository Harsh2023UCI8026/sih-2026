from pathlib import Path
from pypdf import PdfReader, PdfWriter

root = Path(__file__).resolve().parents[2]
source = root / "output" / "pdf"
target = root / "tmp" / "pdfs" / "email_attachments"
target.mkdir(parents=True, exist_ok=True)
common_map = source / "06_Dwarka_Najafgarh_Approx_Pilot_AOI_Map.pdf"
letters = [
    ("01_IMD_DWR_Radar_Data_Request.pdf", "IMD_Radar_Request_and_AOI.pdf"),
    ("02_RMC_Hourly_Rainfall_Availability_Request.pdf", "RMC_Rainfall_Request_and_AOI.pdf"),
    ("03_IFCD_Storm_Drain_Terrain_Records_Request.pdf", "IFCD_Drainage_Terrain_Request_and_AOI.pdf"),
    ("04_MCD_Najafgarh_Local_Drain_Records_Request.pdf", "MCD_Najafgarh_Request_and_AOI.pdf"),
    ("05_PWD_Drain_Road_And_Underpass_Records_Request.pdf", "PWD_Road_Drain_Request_and_AOI.pdf"),
]
for letter_name, packet_name in letters:
    writer = PdfWriter()
    for path in (source / letter_name, common_map):
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    writer.add_metadata({"/Title": packet_name.removesuffix(".pdf").replace("_", " ")})
    out = target / packet_name
    with out.open("wb") as stream:
        writer.write(stream)
    print(f"{out}\t{out.stat().st_size} bytes")
