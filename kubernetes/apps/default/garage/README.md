# [Garage](https://garagehq.deuxfleurs.fr/)

An S3 object store so reliable you can run it outside datacenters

## CLI

The `garage` container does not have shells available. Access with:

```sh
# for k3s deployment
kubectl -n default exec -it deploy/garage -- /garage <command>

# or for the TrueNAS App (assumes ssh'd into truenas server)
docker exec -it ix-garage-garage-1 /garage <command>
```

## Configuration

The k3s-deployed garage serves as a gateway to the TrueNAS app, which serves as the storage manager.

1. Ensure the TrueNAS app has a public-facing RPC. In the app configuration TOML, set:

   ```toml
   rpc_bind_addr ... # whatever is here is fine
   rpc_public_addr = "<truenas public IP>:<same port as above>"
   ```

2. Get the app's node id:

   ```sh
   # while ssh'd into truenas
   docker exec -it ix-garage-garage-1 /garage node id
   ```

3. Tell the k3s garage to connect to the TrueNAS garage

   ```sh
   kubectl -n default exec -it deploy/garage -- /garage node connect <address from above>
   ```

4. Check work

   ```sh
   kubectl -n default exec -it deploy/garage -- /garage status
   ```

5. Set k3s garage as gateway in the truenas garage webui (`http://<truenas_ip>:30186`)
