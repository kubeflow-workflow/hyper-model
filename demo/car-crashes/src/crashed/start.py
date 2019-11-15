import logging
import os
from typing import Dict, List
from hypermodel import hml
from flask import request

# Import my local modules
from crashed import shared, pipeline, inference


def main():
    # Create a reference to our "App" object which maintains state
    # about both the Inference and Pipeline phases of the model
    if "DOCKERHUB_IMAGE" in os.environ and "CI_COMMIT_SHA" in os.environ:
        image_url = os.environ["DOCKERHUB_IMAGE"] + ":" + os.environ["CI_COMMIT_SHA"]
    else:
        image_url = None

    app = hml.HmlApp(
        name="car-crashes",
        platform="GCP",
        image_url=image_url,
        package_entrypoint="crashed",
        inference_port=8000,
        k8s_namespace="kubeflow",
    )
    # Set up Environment Varialbes that will apply to all containers...
    app.with_envs(
        "GCP_PROJECT": "grwdt-dev",
        "GCP_ZONE": "australia-southeast1-a",
        "K8S_CLUSTER": "kf-crashed",
        "K8S_NAMESPACE": "kubeflow",

        "LAKE_BUCKET": "grwdt-dev-lake",
        "LAKE_PATH": "hypermodel/demo/car-crashes",
        "WAREHOUSE_DATASET": "crashed",
        "WAREHOUSE_LOCATION": "australia-southeast1"
    )

    # Create a reference to our ModelContainer, which tells us about
    # the features of the model, where its current version lives and
    # other metadata related to the model.
    crashed_model = shared.crashed_model_container(app)

    # Tell our application about the model we just built a reference for
    app.register_model(shared.MODEL_NAME, crashed_model)

    @hml.pipeline(app.pipelines, cron="0 0 * * *", experiment="demos")
    def crashed_pipeline(message: str = "Hello tez!"):
        """
        This is where we define the workflow for this pipeline purely
        with method invocations.
        """
        # message = "Hello tez!"

        adjusted_message = create_training_op = pipeline.create_training(message=message)
        create_test_op = pipeline.create_test(adjusted_message=adjusted_message)
        train_model_op = pipeline.train_model()

        # Set up the dependencies for this model
        (train_model_op.after(create_training_op).after(create_test_op))

    @hml.deploy_op(app.pipelines)
    def op_configurator(op: hml.HmlContainerOp):
        """
        Configure our Pipeline Operation Pods with the right secrets and 
        environment variables so that it can work with our cloud
        provider's services
        """

        (
            op
            # Service account for authentication / authorisation
            .with_gcp_auth("svcacc-tez-kf")
            # Track where we are going to write our artifacts
            .with_empty_dir("artifacts", "/artifacts")
            # Pass through environment variables from my CI/CD Environment
            # into my container
            .with_env("GITLAB_TOKEN", os.environ["GITLAB_TOKEN"])
            .with_env("GITLAB_PROJECT", os.environ["GITLAB_PROJECT"])
            .with_env("GITLAB_URL", os.environ["GITLAB_URL"])
        )
        return op

    @hml.inference(app.inference)
    def crashed_inference(inference_app: hml.HmlInferenceApp):
        # Get a reference to the current version of my model
        model_container = inference_app.get_model(shared.MODEL_NAME)
        model_container.load()

        # Define our routes here, which can then call other functions with more
        # context
        @inference_app.flask.route("/predict", methods=["GET"])
        def predict():
            logging.info("api: /predict")

            feature_params = request.args.to_dict()
            return inference.predict_alcohol(inference_app, model_container, feature_params)

    @hml.deploy_inference(app.inference)
    def deploy_inference(deployment: hml.HmlInferenceDeployment):
        print(
            f"Preparing deploying: {deployment.deployment_name} ({deployment.k8s_container.image} -> {deployment.k8s_container.args} )"
        )

        (
            deployment.with_gcp_auth("svcacc-tez-kf")
            .with_empty_dir("tmp", "/temp")
            .with_empty_dir("artifacts", "/artifacts")
        )
        pass

    app.start()


# main()
