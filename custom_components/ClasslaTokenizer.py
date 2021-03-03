from typing import Any, Dict, List, Text

from rasa.nlu.tokenizers.tokenizer import Token, Tokenizer
from rasa.shared.nlu.training_data.message import Message
from functools import reduce
from rasa.nlu.tokenizers.spacy_tokenizer import POS_TAG_KEY

import classla


class ClasslaTokenizer(Tokenizer):

    def __init__(self, component_config: Dict[Text, Any] = None) -> None:
        """Construct a new tokenizer using the classla framework."""

        super().__init__(component_config)
        self.nlp = classla.Pipeline("sl", type="standard", processors="tokenize,pos,lemma")

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        text = message.get(attribute)
        doc = self.nlp(text)
        stanza_tokens = []
        for i in doc.sentences:
            stanza_tokens += i.tokens

        tokens = []
        running_offset = 0
        for t in stanza_tokens:
            word_offset = text.index(t.text, running_offset)
            word_len = len(t.text)
            running_offset = word_offset + word_len
            tokens.append(Token(
                text=t.text,
                start=word_offset,
                lemma=t.words[0].lemma if len(t.words) == 1 else None,
                data={POS_TAG_KEY: t.words[0].pos} if len(t.words) == 1 else None,
            ))
        return tokens
