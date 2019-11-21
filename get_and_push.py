import json
import logging
from datetime import datetime

import requests


def load_config_file(filepath):
    log("loading config.file", logging.INFO)
    with open(filepath, 'r') as config_file:
        return json.load(config_file)


def get_cases_from_kgservice(config_data_json):
    try:
        response = requests.get(
            config_data_json["kgservice"]["url"] + "/api/kg/" + config_data_json["kgservice"]["uuid"] + "/cases",
            None,
            auth=(config_data_json["kgservice"]["user"], config_data_json["kgservice"]["password"]),
            timeout=config_data_json["kgservice"]["timeout"],
            verify=config_data_json["kgservice"]["verify"])
        if response.status_code == 201:
            log("loaded cases from kg-service", logging.INFO)
            return response.json()

        else:
            log("Could not load cases from kg service. Expected response 201 it was " + str(response.status_code),
                logging.ERROR)
            raise Exception("ResponseCode was not 201")
    except Exception as e:
        log(str(e), level=logging.ERROR)
        raise Exception


def get_authorization_token(config_data_json):
    data = {'username': config_data_json["ticketsystem"]["post1"]["username"],
            'password': config_data_json["ticketsystem"]["post1"]["password"]}
    try:
        token = requests.post(config_data_json["ticketsystem"]["post1"]["url"],
                              data=data,
                              headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              timeout=config_data_json["ticketsystem"]["post1"]["timeout"],
                              verify=config_data_json["ticketsystem"]["post1"]["verify"])
        if token.status_code == 200 and isinstance(token.text, str):
            log("received authorisation token", logging.INFO)
            return token.text
        elif not isinstance(token.text, str):
            log("token is no string", logging.ERROR)
            raise Exception
        else:
            log("get_authorization_token did not receive token", logging.ERROR)
            raise Exception
    except Exception as e:
        raise e


def retrieve_all_questions(given_case):
    result = ""
    for question in given_case["questions"]:
        result = result + question["text"] + ": " + question["value"] + "\n"
    return result


def delete_case(case, config_data_json):
    try:
        result = requests.delete(
            config_data_json["kgservice"]["url"] + "/api/kg/" + config_data_json["kgservice"][
                "uuid"] + "/cases/" +
            case["uuid"],
            auth=(config_data_json["kgservice"]["user"], config_data_json["kgservice"]["password"]),
            headers={'Content-Type': 'application/json'},
            timeout=config_data_json["kgservice"]["timeout"],
            verify=config_data_json["kgservice"]["verify"]
        )
        if result.status_code == 201:
            log(case["uuid"] + " deleted", logging.INFO)
        else:
            log(case["uuid"] + " could not delete case. Statuscode:" + str(result.status_code), logging.ERROR)
            raise Exception("ResponseCode was not 201")
    except Exception as e:
        log(case["uuid"] + " case could not be deleted " + str(e), logging.ERROR)
        raise e


def post_case(case, config_data_json, body, header_for_post):
    try:
        result = requests.post(config_data_json["ticketsystem"]["post2"]["url"],
                               None,
                               json=body,
                               headers=header_for_post,
                               verify=config_data_json["ticketsystem"]["post2"]["verify"])
        if result.status_code == 201:
            log(case["uuid"] + " is posted", logging.INFO)
            return True
        else:
            log(case["uuid"] + " could not create ticket. Statuscode:" + str(result.status_code), logging.ERROR)
            return False
    except Exception:
        log(case["uuid"] + " could not create ticket", logging.ERROR)
        return False  # TODO Logging


def build_body_for_post(case, config_data_json):
    name = case["reported_by_name"].split(", ")
    return {
        "values": {
            "TemplateID": config_data_json["ticketsystem"]["body"]["tempid"],
            "First_Name": name[1],
            "Last_Name": name[0],
            "Description": "Mail gemeldet " + case["uuid"],
            "Detailed_Decription": "Full Case: " + "\n"
                                   + "case_id: " + case["uuid"] + "\n"
                                   + "questions: " + "\n"
                                   + retrieve_all_questions(case)
                                   + "event_id: " + str(case["event_id"]) + "\n"
                                   + "event_uuid: " + case["event_uuid"] + "\n"
                                   + "created_at: " + str(case["created_at"]) + "\n"
                                   + "analyze_result: " + str(case["analyze_result"]),
            "z1D_Action": "CREATE"
        }
    }


def post_cases_on_ticketsystem(token, config_data_json, cases):
    log("start processing cases", logging.INFO)
    header_for_post = {'Authorization': token, 'Content-Type': 'application/json'}
    for case in cases:
        log(case["uuid"] + " could not create ticket", logging.INFO)
        body = build_body_for_post(case)
        case_is_posted = post_case(case, config_data_json, body, header_for_post)
        if case_is_posted:
            delete_case(case, config_data_json)
        else:
            log(case["uuid"] + " could not be processed", logging.ERROR)


def log(msg, level):
    msg = str(datetime.now()) + "; " + msg
    print(msg)
    logging.log(level, msg)


def main():
    logging.basicConfig(filename='logs/Scriptlog-' + str(datetime.now()) + '.log', level=logging.INFO)
    log("Script starts", level=logging.INFO)
    config_data = load_config_file('config.json')
    new_cases = get_cases_from_kgservice(config_data)
    authorization_token = get_authorization_token(config_data)
    post_cases_on_ticketsystem(authorization_token, config_data, new_cases)
    log("Script ends", level=logging.INFO)


if __name__ == '__main__':
    main()
