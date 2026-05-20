"""Permission sistemi — izin verme ve reddetme senaryoları (mock ile)."""

from agentlite import Agent, tool


# ─── ARAÇLAR ──────────────────────────────────────────────────
@tool(read_only=True)
def list_files(path: str) -> list[str]:
    """Klasördeki dosyaları listele (zararsız)."""
    return ["a.txt", "b.txt", "c.txt"]


@tool(requires_confirmation=True)
def delete_file(path: str) -> str:
    """Bir dosyayı SİL (geri alınamaz!)."""
    return f"{path} silindi (sahte)"


# ─── MOCK CLIENT — modelin delete_file çağırmasını simüle eder ──
class _Block:
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)

class _Response:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason

class MockClient:
    def __init__(self):
        self.messages = self
        self.call = 0

    def create(self, **kwargs):
        self.call += 1
        if self.call == 1:
            # Model: "delete_file çağırmak istiyorum"
            return _Response(
                content=[_Block(
                    type="tool_use", id="t1",
                    name="delete_file", input={"path": "/önemli/dosya.txt"},
                )],
                stop_reason="tool_use",
            )
        # 2. çağrı — sonucu görüp final cevap
        son = kwargs["messages"][-1]
        return _Response(
            content=[_Block(type="text", text=f"İşlem sonucu: {son}")],
            stop_reason="end_turn",
        )


# ─── SENARYO 1: KULLANICI HEP EVET DER ─────────────────────────
def evet_diyen(tool, args):
    print(f"  ✋ [izin sorusu] '{tool.name}' çalıştırılsın mı? ({args})")
    print(f"  ✅ [otomatik] EVET")
    return True


# ─── SENARYO 2: KULLANICI HEP HAYIR DER ────────────────────────
def hayir_diyen(tool, args):
    print(f"  ✋ [izin sorusu] '{tool.name}' çalıştırılsın mı? ({args})")
    print(f"  ❌ [otomatik] HAYIR")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("SENARYO 1: kullanıcı EVET diyor → tool çalışır")
    print("=" * 60)
    a1 = Agent(
        model="x",
        tools=[list_files, delete_file],
        confirm_fn=evet_diyen,
        client=MockClient(),
    )
    print(f"Final: {a1.run('Şu dosyayı sil')}")

    print("\n" + "=" * 60)
    print("SENARYO 2: kullanıcı HAYIR diyor → tool reddedilir")
    print("=" * 60)
    a2 = Agent(
        model="x",
        tools=[list_files, delete_file],
        confirm_fn=hayir_diyen,
        client=MockClient(),
    )
    print(f"Final: {a2.run('Şu dosyayı sil')}")
