# coding=utf-8
import oss2
import gl

class Upload_oss:
    def __init__(self):

        # my oss
        self.__auth = oss2.Auth('key', gl.OSS_KEY)
        self.__bucket = oss2.Bucket(self.__auth, gl.OSS_BUCKET_HTTP, gl.OSS_BUCKET_PATH)
        self.__path = '自定义根目录'

    def upload(self, file_name, file_local_path, types):
        url = '*****/study/lagou/'
        oss_file_name = self.__path+types+'/'+file_name
        res = self.__bucket.put_object_from_file(
            oss_file_name, file_local_path)
        if res.status == 200:
            print('\033[7;32m上传阿里云OSS成功，keyName：'+str(res.crc)+'\033[1;31;40m')
            return url+file_name


if __name__ == "__main__":
    run = Upload_oss()
    file_name = "ceshi.pdf"
    file_local_path = 'C:\\Users\\Desktop\\code\\pdf\\'+file_name
    result = run.upload(file_name, file_local_path,'pdf')
    print(result)
