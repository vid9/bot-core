# -*- coding: utf-8 -*-
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import datetime as dt
import json
import locale
import math
import re
import random
from typing import Any, Dict, List, Text, Optional

import classla
import dateparser
from rasa_sdk.types import DomainDict

from actions.helpers import reminder_helper as rh, weather_helper as wh, news_helper as nh, tv_helper as tvh, traffic_helper as th, list_helper, logic_helper as lh
# from helpers import reminder_helper as rh, weather_helper as wh, news_helper as nh, tv_helper as tvh, traffic_helper as th, list_helper, logic_helper as lh

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import ReminderCancelled, ReminderScheduled, UserUtteranceReverted, ConversationPaused, SlotSet, \
    EventType, ActiveLoop, FollowupAction
from rasa_sdk.executor import CollectingDispatcher

INTENT_DESCRIPTION_MAPPING_PATH = "actions/intent_description_mapping.csv"
# INTENT_DESCRIPTION_MAPPING_PATH = "intent_description_mapping.csv"

locale.setlocale(category=locale.LC_ALL, locale="sl_SI.UTF-8")

pipelineCache = []
# pipelineCache = classla.Pipeline("sl", processors="tokenize,pos,lemma")


def tokenize(text) -> List[str]:
    global pipelineCache
    if pipelineCache:
        doc = pipelineCache(text)
    else:
        # classla.download('sl')
        pipelineCache = classla.Pipeline("sl", processors="tokenize,pos,lemma")
        # pipelineCache = classla.Pipeline("sl", processor# s="tokenize,pos,lemma")
        doc = pipelineCache(text)
    stanza_tokens = []
    for i in doc.sentences:
        stanza_tokens += i.tokens

    lemmas = []
    for t in stanza_tokens:
        lemmas.append(t.words[0].lemma if len(t.words) == 1 else None)
    return lemmas


class ActionDate(Action):
    def name(self) -> Text:
        return "action_date"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        date = dt.datetime.today()
        for i in tracker.latest_message['entities']:
            if i['entity'] == "day":
                day = lh.get_day_number(i['value'])
                date = date + dt.timedelta(days=day)
        date1 = date.strftime("%A, %d. %B %Y")
        dispatcher.utter_message(f"{date1}.")
        return [SlotSet("day", None)]


class ActionDefaultFallBack(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Fallback caused by TwoStageFallbackPolicy
        if len(tracker.events) >= 4 and tracker.events[-4].get("name") == "action_default_ask_affirmation":

            dispatcher.utter_message(template="utter_restart_with_button")
            return [ConversationPaused()]

        # Fallback caused by Core
        else:
            dispatcher.utter_message(template="utter_default")
            return [UserUtteranceReverted()]


class ActionDefaultAskAffirmation(Action):
    """Asks for an affirmation of the intent if NLU threshold is not met."""

    def name(self) -> Text:
        return "action_default_ask_affirmation"

    def __init__(self) -> None:
        import pandas as pd

        self.intent_mappings = pd.read_csv(INTENT_DESCRIPTION_MAPPING_PATH, delimiter=';')
        self.intent_mappings.fillna("", inplace=True)
        self.intent_mappings.entities = self.intent_mappings.entities.map(
            lambda entities: {e.strip() for e in entities.split(",")}
        )

    def get_button_title(self, intent: Text, entities: Dict[Text, Text]) -> Text:
        default_utterance_query = self.intent_mappings.intent == intent
        utterance_query = (self.intent_mappings.entities == entities.keys()) & (
            default_utterance_query
        )

        utterances = self.intent_mappings[utterance_query].button.tolist()

        if len(utterances) > 0:
            button_title = utterances[0]
        else:
            utterances = self.intent_mappings[default_utterance_query].button.tolist()
            button_title = utterances[0] if len(utterances) > 0 else intent
        return button_title.format(**entities)

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[EventType]:

        intent_ranking = tracker.latest_message.get("intent_ranking", [])
        if len(intent_ranking) > 2:
            diff_intent_confidence = intent_ranking[1].get("confidence") - intent_ranking[2].get("confidence")
            if diff_intent_confidence < 0.2:
                intent_ranking = intent_ranking[1:3]
            else:
                intent_ranking = intent_ranking[1:2]
        elif len(intent_ranking) > 1:
            intent_ranking = intent_ranking[1]

        # for the intent name used to retrieve the button title, we either use
        # the name of the name of the "main" intent, or if it's an intent that triggers
        # the response selector, we use the full retrieval intent name so that we
        # can distinguish between the different sub intents
        first_intent_names = [
            intent.get("name", "")
            if intent.get("name", "") not in ["chitchat"]
            else tracker.latest_message.get("response_selector")
            .get(intent.get("name", ""))
            .get("full_retrieval_intent")
            for intent in intent_ranking
        ]
        if first_intent_names[0] is None:
            dispatcher.utter_message(response="utter_default")
            return [UserUtteranceReverted()]

        message_title = (
            "Oprosti, nisem prepričan, če sem pravilno razumel kaj mi želiš povedati 🤔 Si hotel reči..."
        )

        entities = tracker.latest_message.get("entities", [])
        entities = {e["entity"]: e["value"] for e in entities}

        entities_json = json.dumps(entities)

        buttons = []
        for intent in first_intent_names:
            button_title = self.get_button_title(intent, entities)
            if "/" in intent:
                # here we use the button title as the payload as well, because you
                # can't force a response selector sub intent, so we need NLU to parse
                # that correctly
                buttons.append({"title": button_title, "payload": button_title})
            else:
                buttons.append(
                    {"title": button_title, "payload": f"/{intent}{entities_json}"}
                )

        buttons.append({"title": "Nekaj drugega", "payload": "/out_of_scope"})

        dispatcher.utter_message(text=message_title, buttons=buttons)

        return []


def get_light_name(light_name):
    try:
        if len(light_name.split()) == 1:
            return tokenize(light_name)[0]
        return light_name
    except IndexError as e:
        return light_name


class ActionLights(Action):
    def name(self) -> Text:
        return "action_lights_interaction"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        intent_on = tracker.get_slot("light_on")
        intent_off = tracker.get_slot("light_off")
        light_name = ""
        for i in tracker.latest_message['entities']:
            if i['entity'] == "light_name":
                light_name = i['value']
        if not light_name:
            dispatcher.utter_message("Prišlo je do napake. Lahko prosim preoblikuješ stavek?")
        light_name = get_light_name(light_name)
        if intent_on:
            if not light_name:
                message = "Katero luč želiš prižgati?"
            else:
                message = "Ne morem prižgati luči z imenom " + light_name + ". Želiš pod tem imenom dodati novo luč?"
        elif intent_off:
            if not light_name:
                message = "Katero luč želiš ugasniti?"
            else:
                message = "Ne morem izklopiti luči z imenom " + light_name + ". Želiš pod tem imenom dodati novo luč?"
        else:
            message = "Želiš ustvariti novo luč z imenom " + light_name + "?"
        dispatcher.utter_message(message)
        return [SlotSet("light_on", None), SlotSet("light_off", None)]


# class ActionLightName(Action):
#     def name(self) -> Text:
#         return "action_light_name"
#
#     def run(
#             self,
#             dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:
#         intent = tracker.latest_message['intent'].get('name')
#         if intent == "lights_on":
#             dispatcher.utter_message("Katero luč želiš prižgati?")
#             return [SlotSet("light_action", "on")]
#         else:
#             dispatcher.utter_message("Katero luč želiš ugasniti?")
#             return [SlotSet("light_action", "off")]


class ActionWeatherForecast(Action):
    def name(self) -> Text:
        return "action_weather_forecast"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        date_day = tracker.get_slot("day")
        for i in tracker.latest_message['entities']:
            if i['entity'] == "day":
                date_day = i['value']
        location = tracker.get_slot("location")
        if location is None:
            dispatcher.utter_message("Nisem dobro razumel lokacije. Lahko prosim preoblikuješ stavek?")
        if len(location.split()) == 1:
            location = tokenize(location)[0]
        if date_day is None:
            date_day = "danes"
        # lemmas = tokenize(f"{date_day} {location}")
        date_number = lh.get_day_number(tokenize(date_day)[0])
        if type(date_number) is not int:
            dispatcher.utter_message(
                "Prosim zapiši dan z besedo. Na primer ˝danes˝ ali pa ˝ponedeljek˝.")
            return []
        if date_number > 7:
            dispatcher.utter_message(
                "Trenutno lahko poiščem vremensko napoved samo za sedem dni naprej. Za kateri dan te zanima napoved?")
            return []
        # Get current weather for extracted location """
        weather_obj = wh.get_forecast_weather(location, int(date_number))
        if weather_obj["type"] == "error":
            dispatcher.utter_message(weather_obj["description"])
            return []
        forecast_day = dt.datetime.today() + dt.timedelta(days=int(date_number))
        elements = wh.format_weather_forecast(weather_obj)
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(text=f"{weather_obj['name']} {forecast_day.strftime('%A %#d. %B')}.",
                                     elements=elements)
        else:
            dispatcher.utter_message(text=f"{weather_obj['name']} {forecast_day.strftime('%A %#d. %B')}.")
            text = f"{weather_obj['description'].capitalize()} bo. Najvišja temperatura {weather_obj['daily_max']} °C, najnižja {weather_obj['daily_min']} °C. \n\r" \
                   f"🌅 {dt.datetime.fromtimestamp(weather_obj['sunrise']).strftime('%#H:%M')} \n\r" \
                   f"🌇 {dt.datetime.fromtimestamp(weather_obj['sunset']).strftime('%#H:%M')} \n\r" \
                   f"🌧 {round(weather_obj['pop'] * 100)}% \n\r" \
                   f"Vlažnost {weather_obj['humidity']}% \n\r" \
                   f"Pritisk {weather_obj['pressure']} hPa \n\r" \
                   f"Veter {weather_obj['wind_speed']} km/h {weather_obj['wind_direction']}"
            dispatcher.utter_message(text)
        return []


class ActionWeatherCurrent(Action):
    def name(self) -> Text:
        return "action_weather_current"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        location = tracker.get_slot("location")
        if location is None:
            dispatcher.utter_message("Nisem dobro razumel kraja. Lahko prosim preoblikuješ stavek?")
        if len(location.split()) == 1:
            dispatcher.utter_message(" ".join(tokenize(location)))
            location = tokenize(location)[0]

        # if location == "Slovenija" or location == "slovenija":
        #     # Get forecast for Slovenia
        #     return wh.get_forecast_slovenia(dt.datetime.today().weekday())
        #
        # # Get current weather for extracted location
        weather_obj = wh.get_current_weather(location)
        if weather_obj["type"] == "error":
            dispatcher.utter_message(weather_obj["description"])
            return []
        elements = wh.format_weather_current(weather_obj)
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(text=f"Trenutno vremenske razmere v kraju {weather_obj['name']}.", elements=elements)
        else:
            dispatcher.utter_message(text=f"Trenutno vremenske razmere v kraju {weather_obj['name']}: {elements[0]['title']}")
            text = f"Občutek zunaj {weather_obj['temperature_feel']} °C \n\rVlažnost {weather_obj['humidity']}% \n\rPritisk {weather_obj['pressure']} hPa \n\rVeter {weather_obj['wind_speed']} km/h {weather_obj['wind_direction']}"
            dispatcher.utter_message(text)
        return []


class ActionTime(Action):
    def name(self) -> Text:
        return "action_time"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        today = dt.datetime.now()
        dt_hours = today.hour
        dt_minutes = today.minute
        dispatcher.utter_message(f"Ura je {dt_hours}:{today.strftime('%M')}.")
        return []


class ActionRestart(Action):
    """Restarts current conversation"""

    def name(self) -> Text:
        return "action_restart"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        return [...]


class ActionResetReminderSlots(Action):
    def name(self):
        return "action_reset_reminder_slots"

    def run(self, dispatcher, tracker, domain):
        return [SlotSet("reminder_name", None), SlotSet("reminder_date", None), SlotSet("reminder_time", None)]


class ActionSetReminder(Action):
    """Schedules a reminder, supplied with the last message's entities."""

    def name(self) -> Text:
        return "action_set_reminder"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        reminder_name = tracker.get_slot("reminder_name") + tracker.sender_id
        entities = {"reminder_name": tracker.get_slot("reminder_name")}
        print(entities)
        date = dateparser.parse(tracker.get_slot("reminder_date") + " " + tracker.get_slot("reminder_time"))
        reminder = ReminderScheduled(
            "EXTERNAL_reminder",
            trigger_date_time=date,
            entities=entities,
            name=reminder_name,
            kill_on_user_message=False,
        )
        res = rh.save_reminder(tracker.get_slot("reminder_name"), tracker.sender_id, date)
        if res:
            dispatcher.utter_message(
                f"Opomnik ˝{tracker.get_slot('reminder_name')}˝ je nastavljen za {date.strftime('%d. %m. %Y ob %H:%M')}")
            return [reminder,
                    SlotSet("reminder_name", None),
                    SlotSet("reminder_date", None),
                    SlotSet("reminder_time", None)]
        else:
            dispatcher.utter_message("Prišlo je do napake, opomnik ni bil ustvarjen")
            return []


class ValidateReminderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_reminder_form"

    async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Optional[List[Text]]:
        required_slots = ["reminder_name", "reminder_date", "reminder_time"]
        return required_slots

    def validate_reminder_name(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate if this name is available."""
        name = tracker.latest_message.get("text")
        result = rh.get_reminder(tracker.sender_id, name)
        if result:
            dispatcher.utter_message("Opomnik s tem imenom že obstaja. Prosim izberi drugo ime.")
            return {"reminder_name": None}
        else:
            return {"reminder_name": name}

    def validate_reminder_date(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate date and time value."""
        str_day = None
        str_date = None
        print(tracker.latest_message['entities'])
        for i in tracker.latest_message['entities']:
            if i['entity'] == "date_number":
                str_date = i['value']
            if i['entity'] == "day":
                str_day = i['value'].lower()

        if str_day:
            date = lh.get_day_date(str_day)
            if date:
                return {"reminder_date": date}
            dispatcher.utter_message(
                f"Datuma ne prepoznam, prosim zapiši ga v obliki {dt.datetime.now().day} {dt.datetime.now().month}!")
            return {"reminder_date": None}


        date = rh.validate_date(str_date)
        if type(date) is str:
            # validation succeeded, set the value of the "date_number" slot to value
            return {"reminder_date": date}
        else:
            if date == 1:
                dispatcher.utter_message(
                    f"Datuma ne prepoznam, prosim zapiši ga v obliki {dt.datetime.now().strftime('%d. %m.')}!")
            else:
                dispatcher.utter_message("Datum opomnika je v preteklosti. Prosim izberi nov datum.")
            return {"reminder_date": None}

    def validate_reminder_time(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate date and time value."""
        if tracker.get_slot("reminder_date") is None:
            return {"reminder_time": None}
        time_string = tracker.latest_message.get("text")
        if re.search('ur', time_string, re.IGNORECASE) or re.search('min', time_string, re.IGNORECASE) or re.search('sekund', time_string, re.IGNORECASE):
            dispatcher.utter_message(
                f"Ure ne prepoznam, prosim zapiši jo v obliki {dt.datetime.now().strftime('%H:%M')}!")
            return {"reminder_time": None, "time_number": None}
        time = rh.validate_time(
            f"{tracker.get_slot('reminder_date')} {tracker.get_slot('time_number').replace('h', ':00')}")

        if type(time) is str:
            # validation succeeded, set the value of the "reminder_date" slot to value
            return {"reminder_time": time}
        else:
            if time == 1:
                dispatcher.utter_message(
                    f"Ure ne prepoznam, prosim zapiši jo v obliki {dt.datetime.now().strftime('%H:%M')}!")
            else:
                dispatcher.utter_message("Ura opomnika je v preteklosti. Prosim izberi novo uro.")
            return {"reminder_time": None}


class ActionReactToReminder(Action):
    """Reminds the user to call someone."""

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        name = ""
        for i in tracker.latest_message['entities']:
            if i['entity'] == "reminder_name":
                name = i["value"]
        rh.remove_reminder(name, tracker.sender_id)
        dispatcher.utter_message(f"Opomnik: {name}")
        return []


class ShowAllReminders(Action):
    """Gets all currently set reminders."""

    def name(self) -> Text:
        return "action_show_all_reminders"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        print(tracker.sender_id)
        res = rh.get_all_reminders(tracker.sender_id)
        print(res)
        if not res:
            dispatcher.utter_message("Trenutno nimaš nastavljenih opomnikov. Želiš ustvariti nov opomnik?")
            return []
        message = "Tvoji trenutni opomniki:\n"
        for opomnik in res:
            message += f"- {opomnik[1]}, {opomnik[2].strftime('%d. %m. %Y ob %H:%M')}\n"
        dispatcher.utter_message(message)
        return []


class RemoveReminder(Action):
    """Cancels the reminder."""

    def name(self) -> Text:
        return "action_remove_reminder"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        full_string = ""
        reminder_name = ""
        if tracker.get_slot("reminder_name"):
            full_string = tracker.get_slot("reminder_name")
        else:
            if tracker.latest_message.get("entities"):
                for i in tracker.latest_message['entities']:
                    if i['entity'] == "reminder_name":
                        full_string = i["value"]
            else:
                full_string = tracker.latest_message.get("text")
        res = rh.get_all_reminders(tracker.sender_id)
        if not res:
            dispatcher.utter_message("Trenutno nimaš opomnikov. Želiš ustvariti nov opomnik?")
            return []
        reminder_id = -1
        for i in res:
            substring = i[1]
            if substring in full_string:
                reminder_id = i[0]
                reminder_name = substring
                break
        if reminder_id > 0:
            result = rh.remove_reminder_by_id(reminder_id)
            if not result:
                dispatcher.utter_message(f"Prišlo je do napake, opomnik ˝{reminder_name}˝ ni bil odstranjen.")
                return []
            dispatcher.utter_message(f"Opomnik z imenom ˝{reminder_name}˝ je bil odstranjen.")
            return [ReminderCancelled(f"{result}{tracker.sender_id}")]
        else:
            buttons = []
            quick_reply = []
            for opomnik in res:
                title = opomnik[1]
                entities = {"reminder_name": opomnik[1]}
                payload = f"/remove_reminder{json.dumps(entities)}"
                quick_reply.append({
                        "content_type": "text",
                        "title": title,
                        "payload": payload,
                    })
                buttons.append({"title": title, "payload": payload})
            if tracker.get_latest_input_channel() == 'facebook':
                message = {
                    "text": "Kateri opomnik želiš odstraniti?",
                    "quick_replies": quick_reply
                }
                dispatcher.utter_message(json_message=message)
            else:
                dispatcher.utter_message(text="Kateri opomnik želiš odstraniti?", buttons=buttons)


class CurrentNews(Action):
    """Shows current news."""

    def name(self) -> Text:
        return "action_current_news"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        elements = nh.format_news(nh.get_latest_news())
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(text="Zadnje novice iz portala MMC RTV SLO:", elements=elements)
        else:
            dispatcher.utter_message(text="Zadnje novice iz portala MMC RTV SLO:")
            dispatcher.utter_message(attachment=create_carousel(elements))
        return []


class CurrentNewsByCategory(Action):
    """Shows the latels news in category."""

    def name(self) -> Text:
        return "action_current_news_by_category"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        category = tracker.get_slot("news_category")
        result = nh.get_latest_news_by_category(category)
        if not result or result is None:
            dispatcher.utter_message(text=f"V kategoriji ˝{category}˝ ni nobene nove novice.")
            return [SlotSet("news_category", None)]
        elements = nh.format_news(result)
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(text=f"Zadnje novice v kategoriji ˝{category}˝", elements=elements)
        else:
            dispatcher.utter_message(text=f"Zadnje novice v kategoriji ˝{category}˝")
            dispatcher.utter_message(attachment=create_carousel(elements))
        return []


class NewsSubscribe(Action):
    """Subscribe to daily news."""

    def name(self) -> Text:
        return "action_news_subscribe"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        user_reminder = nh.check_user_subscription(tracker.sender_id)
        reminder_name = "subscribe_news" + tracker.sender_id
        date = dt.datetime.now()
        trigger_date = dt.datetime(date.year, date.month, date.day, 18, 0, 0)
        if date > trigger_date:
            trigger_date = trigger_date + dt.timedelta(days=1)
        reminder = ReminderScheduled(
            "EXTERNAL_news",
            trigger_date_time=trigger_date,
            name=reminder_name,
            kill_on_user_message=False,
        )
        if user_reminder:
            dispatcher.utter_message("Na dnevne novice si že prijavljen. Pošiljal ti jih bom ob vsak večer ob 18h.")
        else:
            dispatcher.utter_message(
                "Prijavil si se na dnevno poročilo o aktualnih novicah 📰. Pošiljal ti ga bom ob vsak večer ob 18h.")
            nh.save_news_subscription(reminder_name, tracker.sender_id, trigger_date)
            print(reminder)
        return [reminder]


class ActionReactToNewsSubscription(Action):
    """Remove current news reminder and create a new one. Call action top news."""

    def name(self) -> Text:
        return "action_react_to_news_subscription"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        print("External news is here")
        nh.remove_news_subscription("subscribe_news" + tracker.sender_id, tracker.sender_id)
        reminder_name = "subscribe_news" + tracker.sender_id
        date = dt.datetime.today() + dt.timedelta(days=1)
        trigger_date = dt.datetime(date.year, date.month, date.day, 18, 0, 0)
        reminder = ReminderScheduled(
            "EXTERNAL_news",
            trigger_date_time=trigger_date,
            name=reminder_name,
            kill_on_user_message=False,
        )

        nh.save_news_subscription(reminder_name, tracker.sender_id, trigger_date)
        elements = nh.format_news(nh.get_top_news())
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(text="Najbolj brane novice na portalu MMC RTV SLO:", elements=elements)
        else:
            dispatcher.utter_message(text=f"Najbolj brane novice na portalu MMC RTV SLO:")
            dispatcher.utter_message(attachment=create_carousel(elements))
        return [reminder]


class NewsUnSubscribe(Action):
    """Unsubscribe from daily news."""

    def name(self) -> Text:
        return "action_news_unsubscribe"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        nh.remove_news_subscription("subscribe_news" + tracker.sender_id, tracker.sender_id)
        dispatcher.utter_message(
            "Ok, ne bom ti več pošiljal dnevnih novic. Nanje se lahko spet prijaviš kadarkoli želiš.")
        reminder_name = "subscribe_news" + tracker.sender_id
        return [ReminderCancelled(name=reminder_name)]


class TrafficConditions(Action):
    """Fetches current condition on the road."""

    def name(self) -> Text:
        return "action_traffic"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        traffic = th.get_latest_traffic()
        print(traffic)
        # elements = th.format_traffic(traffic[0], traffic[1])
        dispatcher.utter_message(
            text=f"{traffic[0][0]} \n\r{traffic[0][1]} \n\rVeč informacij na https://www.promet.si/portal/sl/razmere.aspx")
        return []


class TvCurrentlyPlaying(Action):
    """Get currently played show on tv."""

    def name(self) -> Text:
        return "action_tv_curretly_playing"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        program_name = tracker.get_slot("program")
        res = tvh.get_currently_playing(program_name)

        if res:
            elements = tvh.format_schedule(res)
            if tracker.get_latest_input_channel() == 'facebook':
                dispatcher.utter_message(text=f"Trenutno na programu {program_name}", elements=elements)
            else:
                dispatcher.utter_message(text=f"Trenutno na programu {program_name}")
                dispatcher.utter_message(attachment=create_carousel(elements))
            return []
        else:
            dispatcher.utter_message(
                f"Za program {program_name} nisem našel nobenih podatkov. Ti lahko poiščem podatke za kateri drug program?")
            return [SlotSet("program", None)]


class TvSchedule(Action):
    """Gets the schedule for a tv program.
        :parameter
            program (tv program name)
            day (day of the week)
    """

    def name(self) -> Text:
        return "action_tv_schedule"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        program_name = tracker.get_slot("program")

        # Transform user text to day number in week
        day_number = lh.get_day_number(tracker.get_slot("day"))
        day_absolute = check_day(day_number)

        # If day was wrong tell the user why
        if type(day_absolute) is str:
            dispatcher.utter_message(day_absolute)
            return []

        response = tvh.get_schedule_for_program(program_name, day_absolute)
        if not response or response is None:
            dispatcher.utter_message(
                f"Za program {program_name} nisem našel nobenih podatkov o sporedu. Želiš, da poiščem spored za kateri drug program?")
            return [SlotSet("program", None)]
        else:
            elements = tvh.format_schedule(response)
            if math.floor(len(elements) / 10) == 0:
                print("manj kot 10")
                if tracker.get_latest_input_channel() == 'facebook':
                    dispatcher.utter_message(text=response[0][7], elements=elements)
                else:
                    dispatcher.utter_message(text=response[0][7])
                    dispatcher.utter_message(attachment=create_carousel(elements))
                return []
            prev = 0
            curr = 0
            dispatcher.utter_message(f"Spored {response[0][7]}")
            for i in range(math.floor(len(elements) / 10)):
                curr += 10
                if tracker.get_latest_input_channel() == 'facebook':
                    dispatcher.utter_message(elements=elements[prev:curr])
                else:
                    dispatcher.utter_message(attachment=create_carousel(elements[prev:curr]))
                dispatcher.utter_message(text=elements, elements=elements)

                prev += 10
            if tracker.get_latest_input_channel() == 'facebook':
                dispatcher.utter_message(elements=elements[prev:])
            else:
                dispatcher.utter_message(attachment=create_carousel(elements[prev:]))
            return []


class TvSearchQuery(Action):
    """Searches for category or a movie."""

    def name(self) -> Text:
        return "action_tv_search_query"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Transform user text to day number in week
        day_number = lh.get_day_number(tracker.get_slot("day"))
        day_absolute = check_day(day_number)

        # If day was wrong tell the user why
        if type(day_absolute) is str:
            dispatcher.utter_message(day_absolute)
            return []

        program_name = tracker.get_slot("program")
        category = tracker.get_slot("category")
        program_name = tvh.program_name_valid(program_name)
        if program_name:
            program_name = program_name[0][0]
        if program_name is None or program_name == "tv":
            response = tvh.get_universal_schedule_for_category(category, day_absolute)
            if not response or response is None:
                dispatcher.utter_message(f"Za kategorijo ˝{category}˝ nisem našel nobenih rezultatov.")
                return [SlotSet("category", None)]
            elements = tvh.format_schedule_with_program(response)
            response_text = f"Spored za kategorijo ˝{category}˝"
        else:
            response = tvh.get_program_schedule_for_category(program_name, category, day_absolute)
            if not response or response is None:
                dispatcher.utter_message(f"Za kategorijo ˝{category}˝ nisem našel nobenih rezultatov.")
                return [SlotSet("category", None)]
            elements = tvh.format_schedule(response)
            response_text = f"Spored za kategorijo ˝{category}˝ na programu {program_name}"

        if math.floor(len(elements)/10) == 0:
            if tracker.get_latest_input_channel() == 'facebook':
                dispatcher.utter_message(text=response_text, elements=elements)
            else:
                dispatcher.utter_message(text=response_text)
                dispatcher.utter_message(attachment=create_carousel(elements))
            return []
        prev = 0
        curr = 0
        dispatcher.utter_message(response_text)

        for i in range(math.floor(len(elements)/10)):
            curr += 10
            if tracker.get_latest_input_channel() == 'facebook':
                dispatcher.utter_message(elements=elements[prev:curr])
            else:
                dispatcher.utter_message(attachment=create_carousel(elements[prev:curr]))
            prev += 10
        if tracker.get_latest_input_channel() == 'facebook':
            dispatcher.utter_message(elements=elements[prev:])
        else:
            dispatcher.utter_message(attachment=create_carousel(elements[prev:]))
        return []


class UpdateUserLists(Action):
    """Updates slots according to user action. Removes or adds lists that use has active."""

    def name(self) -> Text:
        return "action_update_user_lists"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        list_name = tracker.get_slot("list_name")
        # user_lists = tracker.get_slot("user_lists")
        # if not user_lists:
        #     user_lists = []
        # if list_name not in user_lists:
        #     user_lists.append(list_name)
        message = format_list(list_name)
        dispatcher.utter_message(message)
        return [SlotSet("list_item", None)]


class CheckListExits(Action):
    """Check if the list that user wants to delete exists in the database."""

    def name(self) -> Text:
        return "action_remove_list_confirmation"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        user_string = tracker.latest_message.get("text")
        user_lists = list_helper.get_all_user_lists(tracker.sender_id)
        if not user_lists:
            dispatcher.utter_message("Trenutno nimaš nobenega seznama.")
            return [FollowupAction(name='utter_new_list')]
        current_lists = [i[0] for i in user_lists]
        for list_name in current_lists:
            if list_name in user_string:
                dispatcher.utter_message(f"Si prepričan, da želiš odstraniti seznam z imenom ˝{list_name}˝?")
                return [SlotSet("list_name", list_name)]
        if tracker.get_latest_input_channel() == 'facebook':
            quick_reply = remove_list_buttons_facebook(current_lists)
            message = {
                "text": "Kateri seznam želiš odstraniti?",
                "quick_replies": quick_reply
            }
            dispatcher.utter_message(json_message=message)
        else:
            buttons = remove_list_buttons(current_lists)
            dispatcher.utter_message(text="Kateri seznam želiš odstraniti?", buttons=buttons)
        return [SlotSet("list_name", None)]


class RemoveList(Action):
    """Removes list."""

    def name(self) -> Text:
        return "action_remove_list"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Todo add to fallback
        list_name = tracker.get_slot("list_name")
        list_id = list_helper.remove_list(list_name, tracker.sender_id)
        if list_id is not None:
            dispatcher.utter_message(f"Ok, izbrisal sem seznam z imenom ˝{list_name}˝.")
            list_helper.remove_list_items(list_id[0][0], tracker.sender_id)
            # user_lists = tracker.get_slot("user_lists").remove(list_name)
            return [SlotSet("list_name", None)]
        else:
            dispatcher.utter_message(f"Prišlo je do napake. Nisem našel seznama z imenom {list_name}.")
        return [SlotSet("list_name", None)]


class ValidateListUpdateForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_list_update_form"

    async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Optional[List[Text]]:
        required_slots = ["list_name", "list_item"]
        return required_slots

    def validate_list_item(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate if this name is available."""
        intent = tracker.latest_message['intent'].get('name')
        if intent == "stop" or intent == "deny":
            return {"list_item": "end"}
        name = tracker.latest_message.get("text")
        current_items = tracker.get_slot("list_items")
        items = current_items
        list_name = list_helper.get_list(tracker.get_slot("list_name"), tracker.sender_id)
        if not list_name or list_name is None:
            dispatcher.utter_message("Seznam, ki ga želiš urediti, ne obstaja!")
            return ActiveLoop(None)
        else:
            list_name = list_name[0][1]
            list_id = list_name[0][0]
        if current_items is str:
            items = [current_items]
        if re.search('odstrani ', name, re.IGNORECASE) or re.search('izbriši ', name, re.IGNORECASE):
            name = re.sub(r'odstrani ', '', name, flags=re.IGNORECASE)
            name = re.sub(r'izbriši ', '', name, flags=re.IGNORECASE)
            res = list_helper.remove_from_list(list_id, name)
            # dispatcher.utter_message(text=f"{list_id} {name}")
            if res is not None:
                dispatcher.utter_message(f"Odstranil sem ˝{name}˝. Še kaj drugega?")
                items.remove(name)
                return {"list_item": None, "list_items": items}
            else:
                dispatcher.utter_message(f"Elementa ˝{name}˝ ni na seznamu.")
                return {"list_item": None, "list_items": items}

        item = add_list_item(name, tracker.get_slot("list_name"), tracker.sender_id)
        items.append(item)
        dispatcher.utter_message(f"Dodal sem ˝{item}˝. Še kaj drugega?")
        return {"list_item": None, "list_items": items}

    def validate_list_name(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        list_name = tracker.get_slot("list_name")
        items = list_helper.get_list_items(list_name)
        list_items = [item for itemname in items for item in itemname]
        if list_name:

            dispatcher.utter_message(f"Urejaš seznam {list_name}. Povej kaj želiš dodati ali odstraniti?")
            return {"list_name": list_name, "list_items": list_items}
        list_name = tracker.latest_message.get("text")
        if list_helper.get_list(list_name, tracker.sender_id):
            dispatcher.utter_message(f"Urejaš seznam {list_name}. Povej kaj želiš dodati ali odstraniti?")
            return {"list_name": list_name, "list_items": list_items}
        else:
            dispatcher.utter_message(f"Nisem našel seznama z imenom {list_name}.")
            return {"list_name": None}


class ActionResetListSlots(Action):

    def name(self):
        return "action_reset_list_slots"

    def run(self, dispatcher, tracker, domain):
        return [SlotSet("list_name", None)]


class ValidateListForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_list_form"

    async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Optional[List[Text]]:
        required_slots = ["list_name", "list_item"]
        return required_slots

    def validate_list_item(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate if this name is available."""
        intent = tracker.latest_message['intent'].get('name')
        if intent == "stop" or intent == "deny":
            return {"list_item": "end"}
        name = tracker.latest_message.get("text")
        current_items = tracker.get_slot("list_items")
        items = current_items
        if not current_items:
            items = []
        elif current_items is str:
            items = [current_items]
        if re.search('odstrani ', name, re.IGNORECASE) or re.search('izbriši ', name, re.IGNORECASE):
            name = re.sub('odstrani ', '', name, flags=re.IGNORECASE)
            name = re.sub('izbriši ', '', name, flags=re.IGNORECASE)
            list_name = list_helper.get_list(tracker.get_slot("list_name"), tracker.sender_id)
            res = None
            if list_name:
                res = list_helper.remove_from_list(list_name[0][0],name)
            if res:
                dispatcher.utter_message(f"Odstranil sem ˝{name}˝. Še kaj drugega?")
                items.remove(name)
                return {"list_item": None, "list_items": items}
            else:
                dispatcher.utter_message(f"Elementa ˝{name}˝ ni na seznamu. Še kaj drugega?")
                return {"list_item": None, "list_items": items}
        item = add_list_item(name, tracker.get_slot("list_name"), tracker.sender_id)
        items.append(item)
        dispatcher.utter_message(f"Dodal sem ˝{item}˝. Želiš dodati še kaj?")
        return {"list_item": None, "list_items": items}

    def validate_list_name(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        list_name = tracker.latest_message.get("text")
        if list_helper.get_list(list_name, tracker.sender_id):
            dispatcher.utter_message(f"Seznam z imenom ˝{list_name}˝ že obstaja. Prosim izberi drugo ime.")
            return {"list_name": None}
        if list_helper.create_list(list_name, tracker.sender_id):
            dispatcher.utter_message(f"Ustvaril sem seznam z imenom ˝{list_name}˝. Kaj želiš dodati na seznam?")
            # user_lists = tracker.get_slot("user_lists")
            # if not user_lists:
            #     user_lists = []
            # user_lists.append(list_name)
            return {"list_name": list_name}
        else:
            dispatcher.utter_message("Prišlo je do napake. Nisem mogel ustvariti seznama.")
            return {"list_name": None}


class ShowAllLists(Action):
    """Gets all currently set lists."""

    def name(self) -> Text:
        return "action_show_all_lists"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        text = tracker.latest_message.get("text")

        user_lists = list_helper.get_all_user_lists(tracker.sender_id)
        if not user_lists:
            dispatcher.utter_message("Trenutno nimaš nobenega seznama. Želiš ustvariti nov seznam?")
            return [SlotSet("list_name", None)]

        current_lists = [i[0] for i in user_lists]
        for list_name in current_lists:
            if list_name in text:
                message = format_list(list_name)
                if not message:
                    dispatcher.utter_message(f"Žal nisem našel seznama z imenom ˝{list_name}˝.")
                    return [SlotSet("list_name", None)]
                dispatcher.utter_message(message)
                return [SlotSet("list_name", list_name)]

        if tracker.get_latest_input_channel() == 'facebook':
            quick_reply = show_list_items_buttons_facebook(current_lists)
            lists = ""
            for name in current_lists:
                lists += f"- {name}\n"
            message = {
                "text": f"Tvoji seznami: \n{lists}",
                "quick_replies": quick_reply
            }
            dispatcher.utter_message(json_message=message)
        else:
            buttons = show_list_items_buttons(current_lists)
            dispatcher.utter_message(text="Tvoji seznami:", buttons=buttons)
        return [SlotSet("list_name", None)]


class ShowListsForDeletion(Action):
    """Lists that are available for removal."""

    def name(self) -> Text:
        return "action_show_removable_lists"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        res = list_helper.get_all_user_lists(tracker.sender_id)
        if not res or res is None:
            dispatcher.utter_message("Trenutno nimaš nobenega seznama. Želiš ustvariti nov seznam?")
            return [SlotSet("list_name", None)]
        current_lists = [i[0] for i in res]
        if tracker.get_latest_input_channel() == 'facebook':
            quick_reply = remove_list_buttons_facebook(current_lists)
            message = {
                "text": "Kateri seznam želiš odstraniti?",
                "quick_replies": quick_reply
            }
            dispatcher.utter_message(json_message=message)
        else:
            buttons = remove_list_buttons(current_lists)
            dispatcher.utter_message(text="Kateri seznam želiš odstraniti?", buttons=buttons)
        return [SlotSet("list_name", None)]


def remove_list_buttons(lists):
    buttons = []
    for name in lists:
        entities = {"list_name": name}
        buttons.append({"title": name, "payload": f"/remove_list{json.dumps(entities)}"})
    return buttons


def remove_list_buttons_facebook(lists):
    quick_reply = []
    for name in lists:
        entities = {"list_name": name}
        quick_reply.append({
            "content_type": "text",
            "title": name,
            "payload": f"/remove_list{json.dumps(entities)}",
        })
    return quick_reply


def show_list_items_buttons(lists):
    buttons = []
    for name in lists:
        entities = {"list_name": name}
        buttons.append({"title": name, "payload": f"/show_list{json.dumps(entities)}"})
    return buttons


def show_list_items_buttons_facebook(lists):
    quick_reply = []
    for name in lists:
        entities = {"list_name": name}
        quick_reply.append({
            "content_type": "text",
            "title": name,
            "payload": f"/show_list{json.dumps(entities)}",
        })
    return quick_reply


class ShowSingleList(Action):
    """Show requested list currently set reminders."""

    def name(self) -> Text:
        return "action_show_list_items"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        list_name = None
        for i in tracker.latest_message['entities']:
            if i['entity'] == "list_name":
                list_name = i['value']
        if not list_name:
            return []
        message = format_list(list_name)
        if not message:
            dispatcher.utter_message(f"Žal nisem našel seznama z imenom ˝{list_name}˝.")
            return [SlotSet("list_name", None)]
        dispatcher.utter_message(message)
        return [SlotSet("list_name", list_name)]


class StartAJoke(Action):
    """Tell a joke to a user."""

    def name(self) -> Text:
        return "action_ask_joke_guess"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        number = random.randint(0, 11)
        joke_first = ["Kaj je hitrost?",
                      "Kaj reče Janez Janša, ko vidi dlako v jajcu?",
                      "Kaj je modro in leta po zraku?",
                      "Zakaj ima policaj mokre čevlje, ko vrže cigareto v vodo?",
                      "Zakaj v gorah vedno gradijo lesene hišice?",
                      "Zakaj ima krava maščobno mleko?",
                      "Kaj leta po zraku in se sveti?",
                      "Kako reče ljudožerec tekačem?",
                      "Kaj je črno, leta po zraku in je zelo nevarno?",
                      "Kaj dobimo če križamo kačo in ježa?",
                      "Kaj nastane, ko dve stoenki padeta v morje?",
                      "Kaj je najboljše pri Švici?"]
        joke_puncline = ["Da polža zanese na ovinku. 🤣",
                         "Glej Kacina.",
                         "Muha v kavbojkah. 😆",
                         "Ker cigareto tudi pohodi. 😆",
                         "Ker jim je zmanjkalo kamna, ker so gradili gore. 🤣",
                         "Da ne škripa, ko jo molzeš. 😂",
                         "Muha z zlatim zobom. 😂",
                         "Fast food. 🤣",
                         "Muha z brzostrelko. 😆",
                         "Bodečo žico. 🤣",
                         "VAL 202. 😆",
                         "Ne vem, ampak zastava je velik plus. 😅"]
        dispatcher.utter_message(joke_first[number])
        return [SlotSet("punchline", joke_puncline[number])]


class FinishAJoke(Action):
    """Tell a joke to a user."""

    def name(self) -> Text:
        return "action_jokepunchline"

    async def run(
            self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(tracker.get_slot("punchline"))
        return [SlotSet("punchline", None), SlotSet("joke_guess", None)]


def format_list(list_name):
    res = list_helper.get_list_items(list_name)
    if not res:
        return None
    message = f"Seznam ˝{list_name}˝"
    if res:
        for item in res:
            message += f"\n- {item[0]}"
    else:
        message += "je prazen."
    return message


def add_list_item(name, list_name, sender_id):
    item = re.sub('dodaj ', '', name, flags=re.IGNORECASE)
    list_helper.add_to_list(
        list_helper.get_list(list_name, sender_id)[0][0],
        item,
        sender_id)
    return item


def check_day(day):
    if day is None:
        return "Nisem razumel dneva. Prosim zapiši ga kot ˝danes˝ ali ˝ponedeljek˝."
    if day > 3:
        return "Spored za ta dan še ne obstaja, poiščem ga lahko le za 3 dni naprej."
    return (dt.datetime.today().weekday() + day) % 7


def create_carousel(elements):
    return {
        "type": "template",
        "payload": {
            "template_type": "generic",
            "elements": elements
        }
    }