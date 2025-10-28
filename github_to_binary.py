import requests, zipfile, io, os, shutil, gzip
from tqdm import tqdm

def download_repo(username, repo, branch):
    zip_url = f"https://github.com/{username}/{repo}/archive/refs/heads/{branch}.zip"
    print(f"📦 Downloading: {zip_url}")
    zip_response = requests.get(zip_url, stream=True)

    if zip_response.status_code != 200:
        print(f"❌ Error downloading ZIP: {zip_response.status_code}")
        return None

    total_size = int(zip_response.headers.get('content-length', 0))
    buffer = io.BytesIO()
    with tqdm(total=total_size, unit='B', unit_scale=True, desc='⬇️ Downloading') as pbar:
        for chunk in zip_response.iter_content(1024):
            buffer.write(chunk)
            pbar.update(len(chunk))

    buffer.seek(0)
    extract_path = f"{repo}_{branch}_extracted"
    with zipfile.ZipFile(buffer) as z:
        z.extractall(extract_path)
    print(f"📂 Extracted to: {extract_path}")
    return extract_path


def encode_repo_to_binary(extract_path, repo, branch):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{repo}_{branch}_binary.txt")

    print("\n⚙️ Converting files to binary...")
    all_files = []
    for root, _, files in os.walk(extract_path):
        for f in files:
            all_files.append(os.path.join(root, f))

    with open(output_file, 'w', encoding='utf-8') as out:
        for filepath in tqdm(all_files, desc="🔄 Converting", unit="file"):
            rel_path = os.path.relpath(filepath, extract_path)
            try:
                with open(filepath, 'rb') as f:
                    binary_data = ''.join(format(byte, '08b') for byte in f.read())
                out.write(f"--- {rel_path} ---\n{binary_data}\n\n")
            except Exception as e:
                print(f"⚠️ Skipped {rel_path} (error: {e})")

    # Compress output for cleanliness
    with open(output_file, 'rb') as f_in:
        with gzip.open(output_file + ".gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Cleanup
    shutil.rmtree(extract_path, ignore_errors=True)
    print(f"\n💾 Saved binary (compressed): {output_file}.gz")
    print("🧹 Cleaned up extracted repo files.")
    print("🎉 Done encoding!\n")


def decode_binary_to_files(binary_file):
    decoded_folder = "decoded_repo"
    os.makedirs(decoded_folder, exist_ok=True)
    print("\n🔄 Decoding binary to files...")

    # Decompress if .gz file
    if binary_file.endswith(".gz"):
        with gzip.open(binary_file, 'rb') as f_in:
            content = f_in.read().decode('utf-8')
    else:
        with open(binary_file, 'r', encoding='utf-8') as f:
            content = f.read()

    parts = content.split('--- ')
    for part in tqdm(parts[1:], desc="📂 Rebuilding files", unit="file"):
        header, *binary_lines = part.split('\n', 1)
        if not binary_lines:
            continue
        filepath = header.replace(' ---', '').strip()
        binary_data = binary_lines[0].strip()

        file_path = os.path.join(decoded_folder, filepath)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            byte_data = bytes(int(binary_data[i:i+8], 2) for i in range(0, len(binary_data), 8))
            with open(file_path, 'wb') as f:
                f.write(byte_data)
        except Exception as e:
            print(f"⚠️ Error decoding {filepath}: {e}")

    print(f"\n✅ Repo reconstructed in: {decoded_folder}")
    print("🎉 Done decoding!\n")


def main():
    while True:
        print("\n🚀 Choose mode:")
        print("1️⃣ Encode (GitHub → Binary)")
        print("2️⃣ Decode (Binary → Repo)")
        print("3️⃣ Exit")

        choice = input("👉 Enter choice: ").strip()
        if choice == "1":
            github_url = input("🔗 Enter GitHub repo URL: ").strip()
            if github_url.endswith('.git'):
                github_url = github_url[:-4]
            parts = github_url.split('/')
            if len(parts) < 2:
                print("❌ Invalid GitHub URL.")
                continue

            username, repo = parts[-2], parts[-1]
            branches_url = f"https://api.github.com/repos/{username}/{repo}/branches"
            res = requests.get(branches_url)
            if res.status_code != 200:
                print("❌ Could not fetch branches.")
                continue

            branches = [b['name'] for b in res.json()]
            print("\n🌿 Branches:")
            for i, br in enumerate(branches, start=1):
                print(f"  {i}. {br}")
            br_choice = int(input("\n👉 Choose branch: ")) - 1
            branch = branches[br_choice]

            extract_path = download_repo(username, repo, branch)
            if extract_path:
                encode_repo_to_binary(extract_path, repo, branch)

        elif choice == "2":
            file_path = input("📁 Enter path to binary (.txt or .gz): ").strip()
            if not os.path.exists(file_path):
                print("❌ File not found.")
                continue
            decode_binary_to_files(file_path)

        elif choice == "3":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("⚠️ Invalid choice.")


if __name__ == "__main__":
    main()
