import docker
import time

client = docker.from_env()

def run_untrusted_model(image, text, timeout=5):
    container = client.containers.run(
        image=image,
        command=[text],
        detach=True,
        read_only=True,
        network_mode="none",
        mem_limit="256m",
        pids_limit=64,
        security_opt=["no-new-privileges"],
        tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"}
    )

    try:
        # Wait for container to finish (with timeout)
        result = container.wait(timeout=timeout)

        # Collect logs AFTER completion
        logs = container.logs(stdout=True, stderr=False)
        return logs.decode()

    except docker.errors.APIError as e:
        container.kill()
        return f"Execution failed: {str(e)}"

    except Exception:
        container.kill()
        return "Execution timed out"

    finally:
        container.remove(force=True)


if __name__ == "__main__":
    print(run_untrusted_model("modelise/example-model:1.0", "hello sandbox"))
