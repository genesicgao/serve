# serve
根据django的serve修改的，可以根据图片url后加参数来缩放或者切割图片，使用时用代替django的serve

# Requirements
> python 2.7
> django
> Pillow

# 参数
//缩略图
URL + '_[width]X[height]'  => http://127.0.0.1:8000/media/demo.png_100X100
//定宽缩略图
URL + '_W[width]' => http://127.0.0.1:8000/media/demo.png_W100
//定高缩略图
URL + '_H[height]' => http://127.0.0.1:8000/media/demo.png_H100
//特殊的w1000缩略图
URL + '_THUMB' => http://127.0.0.1:8000/media/demo.png_THUMB
//限定长边，短边自适应
URL + '_L[long]' => http://127.0.0.1:8000/media/demo.png_L1000
//限定短边，长边自适应
URL + '_S[short]' => http://127.0.0.1:8000/media/demo.png_S500
//限定最大边：（长宽都不超过设定尺寸）
URL + '_MAX[long]' => http://127.0.0.1:8000/media/demo.png_MAX400
//旋转角度：逆时针旋转
URL + '_MAX[long]' => http://127.0.0.1:8000/media/demo.png_MAX400
//原点裁切：以图片原点坐标（0,0）固定尺寸裁切或者按刀数裁切返回原点所在的切片图
'C1-1' => '_C1-1',//表示横向切一刀，竖向切一刀
'C2-3' => '_C2-3',//表示横向切2刀，竖向切3刀
//横/竖向切片，返回任意一张切片（PXm-n）：P为指令符，X表示横向切，Y表示竖向切,m表示被切成的片数，n表示要返回第n张切片图
'PX6-1' => '_PX6-1',//表示横向切成6份，返回第1张切片图
'PY3-2' => '_PY3-2',//表示横向切成3份，返回第2张切片图
//特殊等比缩放格式，目的 保证小图不处理，中等大小图片针对性处理，大图片压缩50%处理
'U512-1024' => '_U512-1024',//表示最大边小于512px则保存原图不变；最大边大于512小于1024，则等比缩放到最大边为512px；最大边大于1024，则将图片尺寸等比压缩至原来的50%；

