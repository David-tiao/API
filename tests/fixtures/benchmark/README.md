# 纯合成评分真值

`ground_truth.synthetic.json` 是 V14 单元测试使用的 5 条虚构接口：T1 两条、T2 一条、T3 两条。域名为文档保留的 `app.example.test` / `api.example.test`，绝不指向评测域名，也不要求访问网络。

本目录只能用于分数公式、路径/方法匹配、FP/FN、权重与稳定性测试。不能将它作为官方 ground truth 或独立站点评分依据。实际工具输出使用 `tests/test_benchmark_pipeline.py` 的独立离线模拟环境生成并评分，未进行互联网请求。
