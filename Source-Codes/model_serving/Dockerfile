FROM tensorflow/serving:latest

COPY tf_models /models
COPY model_serving/models.config /models/models.config

EXPOSE 8501

CMD ["tensorflow_model_server", "--rest_api_port=8501", "--model_config_file=/models/models.config"]
