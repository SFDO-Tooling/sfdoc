from io import BytesIO
from zipfile import ZipFile


def gen_zip_file(file_name, file_contents):
    zip_buff = BytesIO()
    with ZipFile(zip_buff, mode='w') as f_zip:
        f_zip.writestr(file_name, file_contents)
    return zip_buff.getvalue()
