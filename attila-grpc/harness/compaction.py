from fastembed import TextEmbedding

class Embedding:
    def __init__(self):
        self.model = TextEmbedding("Qwen/Qwen3-Embedding-0.6B")

    def generate_vector(self, content):
        embedded = content[:24000]
        return list(self.model.embed([embedded]))[0].tolist()