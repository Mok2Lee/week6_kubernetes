"""Generate a local lab CA and Service certificate; never commit private keys."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'week6-lab-ca')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False,
                                      key_cert_sign=True, crl_sign=True, content_commitment=False,
                                      data_encipherment=False, key_agreement=False,
                                      encipher_only=None, decipher_only=None), critical=True)
          .sign(ca_key, hashes.SHA256()))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'metrics.default.svc')])
    server = (x509.CertificateBuilder().subject_name(server_name).issuer_name(ca_name)
              .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=30))
              .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
              .add_extension(x509.SubjectAlternativeName([x509.DNSName(name) for name in
                  ['metrics', 'metrics.default', 'metrics.default.svc', 'metrics.default.svc.cluster.local']]), critical=False)
              .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
              .sign(ca_key, hashes.SHA256()))
    (destination / 'ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (destination / 'tls.crt').write_bytes(server.public_bytes(serialization.Encoding.PEM))
    (destination / 'tls.key').write_bytes(server_key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (destination / 'tls.key').chmod(0o600)
    # The CA private key is never written, so no root signing key remains on disk.
    print('실습용 통계 서비스 인증서 생성 완료')


if __name__ == '__main__':
    generate(sys.argv[1] if len(sys.argv) > 1 else '/output')
