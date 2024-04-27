#!/usr/bin/env python3

import asyncio
import logging
from typing import Any

import ucapi
import os

import config
import media_player

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages

loop = asyncio.get_event_loop()
api = ucapi.IntegrationAPI(loop)



async def startcheck():
    """
    Called at the start of the integration driver to add a media player entity for all configured cmds list entries in config.py
    """

    for cmd in config.setup.cmds:
        id = config.setup.get("id-"+cmd)
        name = config.setup.get("name-"+cmd)

        if api.available_entities.contains(id):
            _LOG.debug("Entity with id " + id + " is already in storage as available entity")
        else:
            _LOG.info("Add entity with id " + id + " and name " + name + " as available entity")
            await add_mp(id, name)



async def add_mp(id: str, name: str):
    #TODO Only works when in driver.py. When in media_player.py the response to get_available entities is an empty list
    """
    Creates the media player entity definition and adds the entity to the remote via the api

    :param id: media_player entity id
    :param name: media_player entity name
    """

    definition = ucapi.MediaPlayer(
        id, 
        name, 
        [ucapi.media_player.Features.SELECT_SOURCE],
        attributes={},
        cmd_handler=mp_cmd_handler
    )

    api.available_entities.add(definition)

    _LOG.info("Added media player entity with id " + id + " and name " + name)



async def mp_cmd_handler(entity: ucapi.MediaPlayer, cmd_id: str, _params: dict[str, Any] | None) -> ucapi.StatusCodes:
    """
    Media Player command handler.

    Called by the integration-API if a command is sent to a configured media_player-entity.

    :param entity: media_player entity
    :param cmd_id: command
    :param _params: optional command parameters
    :return: status of the command
    """

    if _params == None:
        _LOG.info(f"Received {cmd_id} command for {entity.id}")
    else:
        _LOG.info(f"Received {cmd_id} command with parameter {_params} for {entity.id}")
    
    return media_player.mp_cmd_assigner(entity.id, cmd_id, _params)



@api.listens_to(ucapi.Events.CONNECT)
async def on_r2_connect() -> None:
    """
    Connect notification from Remote Two.

    Just reply with connected as there is no permanent connection to a device that needs to be re-established
    """
    _LOG.info("Received connect event message from remote")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)



@api.listens_to(ucapi.Events.DISCONNECT)
#TODO Find out how to prevent the remote from constantly reconnecting when the integration is not running without deleting the integration configuration on the remote every time
async def on_r2_disconnect() -> None:
    """
    Disconnect notification from the remote Two.

    Just reply with disconnected as there is no permanent connection to a device that needs to be closed
    """
    _LOG.info("Received disconnect event message from remote")
    await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)



@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """
    Enter standby notification from Remote Two.

    Set config.R2_IN_STANDBY to True and show a debug log message as there is no permanent connection to a device that needs to be closed.
    """
    _LOG.info("Received enter standby event message from remote")

    _LOG.debug("Set config.R2_IN_STANDBY to True")
    config.setup.set("standby", True)
    


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """
    Exit standby notification from Remote Two.

    Just show a debug log message as there is no permanent connection to a device that needs to be re-established.
    """
    _LOG.info("Received exit standby event message from remote")

    _LOG.debug("Set config.R2_IN_STANDBY to False")
    config.setup.set("standby", False)



@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """
    Subscribe to given entities.

    :param entity_ids: entity identifiers.

    Just show a debug log message as there are no attributes to update.
    """
    _LOG.info("Received subscribe entities event for entity ids: " + str(entity_ids))

    config.setup.set("standby", False)



@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """
    Unsubscribe to given entities.

    :param entity_ids: entity identifiers.

    Just show a debug log message as there is not device to disconnect.
    """
    _LOG.info("Unsubscribe entities event for entity ids: %s", entity_ids)



async def main():

    logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(name)-14s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("ucapi.api").setLevel(level)
    logging.getLogger("ucapi.entities").setLevel(level)
    logging.getLogger("ucapi.entity").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("media_player").setLevel(level)
    logging.getLogger("setup").setLevel(level)
    logging.getLogger("config").setLevel(level)

    _LOG.debug("Starting driver")
    
    await api.init("setup.json")
    await startcheck()



if __name__ == "__main__":
    loop.run_until_complete(main())
    loop.run_forever()