import kfp.dsl as dsl

@dsl.pipeline(
    name='Prediction pipeline',
    description='Generate slim models and optimize them with OpenVINO'
)
def tf_slim_optimize(
        model_name = dsl.PipelineParam(name='model-name', value='resnet_v1_50'),
        num_classes = dsl.PipelineParam(name='num-classes', value=1000),
        checkpoint_url = dsl.PipelineParam(name='checkpoint-url', value='http://download.tensorflow.org/models/resnet_v1_50_2016_08_28.tar.gz'),
        batch_size = dsl.PipelineParam(name='batch-size', value=1),
        export_dir = dsl.PipelineParam(name='tf-export-dir', value='/tmp/export'),
        generated_model_dir = dsl.PipelineParam(name='generated-model-dir', value='gs://your-bucket/folder'),
        mo_options = dsl.PipelineParam(name='mo-option', value='--saved_model_dir .'),
        input_numpy_file = dsl.PipelineParam(name='input-numpy-file', value='gs://intelai_public_models/images/imgs.npy'),
        label_numpy_file = dsl.PipelineParam(name='label-numpy-file', value='gs://intelai_public_models/images/lbs.npy')):

    slim = dsl.ContainerOp(
        name='Create_model',
        image='intelaipg/kubeflow-pipeline-openvino:0.1',
        command=['python', 'slim_model.py'],
        arguments=[
            '--model_name', model_name,
            '--batch_size', batch_size,
            '--checkpoint_url', checkpoint_url,
            '--num_classes', num_classes,
            '--saved_model_dir', generated_model_dir,
            '--export_dir', export_dir],
        file_outputs={'generated-model-dir': '/tmp/saved_model_dir.txt'})

    mo = dsl.ContainerOp(
        name='Optimize_model',
        image='intelaipg/kubeflow-pipeline-openvino:0.1',
        command=['python','convert_model.py'],
        arguments=[
            '--input_path', '%s/saved_model.pb' % slim.output,
            '--mo_options', mo_options,
            '--output_path', slim.output],
        file_outputs={'bin': '/tmp/bin_path.txt', 'xml': '/tmp/xml_path.txt'})

    dsl.ContainerOp(
        name='openvino-predict',
        image='intelaipg/kubeflow-pipeline-openvino:0.1',
        command=['python', 'predict.py'],
        arguments=[
            '--model_bin', mo.outputs['bin'],
            '--model_xml', mo.outputs['xml'],
            '--input_numpy_file', input_numpy_file,
            '--label_numpy_file', label_numpy_file,
            '--output_folder', generated_model_dir],
        file_outputs={})

if __name__ == '__main__':
    import kfp.compiler as compiler
    compiler.Compiler().compile(tf_slim_optimize, __file__ + '.tar.gz')