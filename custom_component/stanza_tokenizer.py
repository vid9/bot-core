from typing import Any, Dict, List, Text

from rasa.nlu.tokenizers.tokenizer import Token, Tokenizer
from rasa.shared.nlu.training_data.message import Message
from functools import reduce
from rasa.nlu.tokenizers.spacy_tokenizer import POS_TAG_KEY

import stanza


class StanzaTokenizer(Tokenizer):

    defaults = {
        # What language to use
        "lang": "sl",
        # Where to load the model
        "cache_dir": "stanza_resources",
    }

    # the StanzaTokenizer only supports languages from this list
    supported_language_list = [
        "sl",
    ]

   def __init__(self, component_config: Dict[Text, Any] = None) -> None:
        """Construct a new tokenizer using the Stanza framework."""

        super().__init__(component_config)
        self.nlp = stanza.Pipeline(
            lang=component_config["lang"],  # the language model from Stanza to user
            dir=component_config[
                "cache_dir"
            ],  # the caching directory to load the model from
            processors="tokenize,pos,lemma",  # info: https://stanfordnlp.github.io/stanza/pipeline.html#processors
            tokenize_no_ssplit=True,  # disable sentence segmentation
        )

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        text = message.get(attribute)

        doc = self.nlp(text)
        stanza_tokens = reduce(lambda a, b: a + b, doc.sentences).tokens

        return [
            Token(
                text=t.text,
                start=t.start_char,
                end=t.end_char,
                lemma=t.words[0].lemma if len(t.words) == 1 else None,
                data={POS_TAG_KEY: t.words[0].pos} if len(t.words) == 1 else None,
            )
            for t in stanza_tokens
        ]
